import fs from 'fs';
import path from 'path';
import type { Job } from '../../queue/index.js';
import { logger } from '../services/logger';
import { env } from '../config/runtimeEnv';
import { ocr, parser } from '../services/index.js';
import whatsapp from '../services/whatsapp';
import {
	getSession,
	storePendingReceiptData,
	storePendingReceiptForConfirmation,
	formatSummary,
	markConfirmationSent,
	markErrorSent,
	type Session,
} from '../conversation/sessionStore.js';
import sharp from 'sharp';
import {
	resolveReceiptDate,
	stabilizeDate,
	sanitizeCompanyName,
	normalizeDocumentType,
	normalizeDocumentNumber,
	sanitizeTaxId,
} from './receiptHeuristics.js';

function slugify(value?: string | null) {
	if (!value) return null;
	const slug = value
		.toString()
		.trim()
		.toLowerCase()
		.replace(/[^a-z0-9]+/gi, '-')
		.replace(/^-+|-+$/g, '')
		.replace(/-{2,}/g, '-')
		.slice(0, 48);
	return slug || null;
}

function formatDateForSlug(date: Date) {
	const y = date.getFullYear();
	const m = String(date.getMonth() + 1).padStart(2, '0');
	const d = String(date.getDate()).padStart(2, '0');
	return `${y}${m}${d}`;
}

function parseReceiptDate(value?: string | null): Date | null {
	if (!value) return null;
	const trimmed = value.trim();
	if (!trimmed) return null;
	const isoMatch = trimmed.match(/^(\d{4})-(\d{2})-(\d{2})$/);
	if (isoMatch) {
		const year = Number.parseInt(isoMatch[1], 10);
		const month = Number.parseInt(isoMatch[2], 10);
		const day = Number.parseInt(isoMatch[3], 10);
		if (!Number.isNaN(year) && !Number.isNaN(month) && !Number.isNaN(day)) {
			return new Date(year, month - 1, day);
		}
	}
	const parsed = new Date(trimmed);
	if (Number.isNaN(parsed.getTime())) return null;
	return parsed;
}

function extensionFromContentType(contentType?: string | null) {
	if (!contentType) return null;
	if (contentType === 'image/jpeg' || contentType === 'image/jpg') return '.jpg';
	if (contentType === 'image/png') return '.png';
	if (contentType === 'image/heic') return '.heic';
	if (contentType === 'application/pdf') return '.pdf';
	const parts = contentType.split('/');
	if (parts.length === 2) return `.${parts[1]}`;
	return null;
}

function resolveFileExtension(filePath: string | null, mediaContentType?: string | null) {
	const ext = filePath ? path.extname(filePath) : '';
	if (ext) return ext;
	const fromType = extensionFromContentType(mediaContentType);
	if (fromType) return fromType;
	return '.bin';
}

function buildReceiptFilename(
	companyName: string | null,
	documentNumber: string | null,
	receiptDate: string | null,
	jobId: string,
	extension: string,
	fallbackDate: Date,
) {
	const dateValue = parseReceiptDate(receiptDate) ?? fallbackDate;
	const dateSlug = formatDateForSlug(dateValue);
	const companySlug = slugify(companyName) ?? 'recibo';
	const documentSlug = slugify(documentNumber) ?? 'sin-documento';
	const base = `${companySlug}-${documentSlug}-${dateSlug}`;
	const trimmed = base.slice(0, 80) || jobId;
	return `${trimmed}${extension}`;
}

function formatSheetTimestamp(date: Date) {
	const y = date.getFullYear();
	const m = String(date.getMonth() + 1).padStart(2, '0');
	const d = String(date.getDate()).padStart(2, '0');
	const h = String(date.getHours()).padStart(2, '0');
	const min = String(date.getMinutes()).padStart(2, '0');
	return `${y}-${m}-${d} ${h}:${min}`;
}

function pad(value: number) {
	return String(value).padStart(2, '0');
}


async function optimizeBufferForParser(
	buffer: Buffer,
	mediaContentType?: string | null,
): Promise<Buffer> {
	const isImage =
		!mediaContentType ||
		mediaContentType.startsWith('image/jpeg') ||
		mediaContentType.startsWith('image/png') ||
		mediaContentType.startsWith('image/heic');
	if (!isImage) return buffer;
	// Skip tiny buffers to avoid overhead
	if (buffer.length < 512 * 1024) return buffer;

	try {
		const meta = await sharp(buffer).metadata();
		let pipeline = sharp(buffer).rotate();
		const targetMax = 1600;
		if (
			(meta.width && meta.width > targetMax) ||
			(meta.height && meta.height > targetMax)
		) {
			pipeline = pipeline.resize({
				width: targetMax,
				height: targetMax,
				fit: 'inside',
				withoutEnlargement: true,
			});
		}
		return await pipeline.jpeg({ quality: 85 }).toBuffer();
	} catch (err) {
		logger.warn('Image optimization skipped', { error: (err as Error).message });
		return buffer;
	}
}

export async function processReceipt(job: Job) {
	logger.info('Processing job', { id: job.id });

	const from = job.payload?.from;
	const mediaSid = job.payload?.mediaSid;
	if (from) {
		const current = getSession(from);
		if (current?.lastMediaSid && mediaSid && current.lastMediaSid !== mediaSid) {
			logger.info('Skipping stale receipt job', {
				jobId: job.id,
				lastJobId: current.lastJobId,
				lastMediaSid: current.lastMediaSid,
				mediaSid,
				from,
			});
			return;
		}
		if (current?.lastJobId && current.lastJobId !== job.id) {
			logger.info('Skipping stale receipt job', { jobId: job.id, lastJobId: current.lastJobId, from });
			return;
		}
	}

	if (job.payload && job.payload.fail) {
		throw new Error('Simulated failure for testing dead-letter');
	}

	let filePath: string | null = null;
	let buffer: Buffer | null = null;
	let keepTempFile = false;
	const processedAt = new Date();
	try {
		const useMocks = env.USE_MOCK_SERVICES || process.env.USE_MOCK_SERVICES === 'true';

		if (job.payload && job.payload.mediaUrl) {
			if (useMocks) {
				// In mock mode, fetch media without requiring Twilio credentials
				try {
					const res = await fetch(job.payload.mediaUrl);
					if (!res.ok) throw new Error(`mock fetch media failed ${res.status}`);
					buffer = Buffer.from(await res.arrayBuffer());
				} catch (e) {
					logger.warn('Mock media fetch failed, using fake buffer', { error: (e as Error).message });
					buffer = Buffer.from('fake-image-data');
				}
			} else {
				try {
					filePath = await whatsapp.downloadMedia(job.payload.mediaUrl, {
						messageSid: job.payload.messageSid,
						mediaSid: job.payload.mediaSid,
						contentType: job.payload.mediaContentType,
					});
					buffer = fs.readFileSync(filePath);
				} catch (e) {
					const msg = (e as Error).message || String(e);
					logger.warn('Twilio media download failed, falling back to mock buffer', { error: msg });
					// Attempt unauthenticated fetch (may 401) and otherwise use fake buffer so pipeline continues
					try {
						const res = await fetch(job.payload.mediaUrl);
						if (res.ok) {
							buffer = Buffer.from(await res.arrayBuffer());
						} else {
							buffer = Buffer.from('fake-image-data');
						}
					} catch (_err) {
						buffer = Buffer.from('fake-image-data');
					}
				}
			}
		}

		if (!buffer) {
			buffer = filePath ? fs.readFileSync(filePath) : Buffer.from('fake-image-data');
		}

		let text = '';
		if (useMocks) {
			try {
				text = await ocr.recognize(buffer);
				logger.info('OCR text', { text });
			} catch (err) {
				logger.warn('OCR recognize failed in mock mode', { error: (err as Error).message });
			}
		}

		const parserBuffer = useMocks
			? buffer
			: await optimizeBufferForParser(buffer, job.payload?.mediaContentType);

		const parsed = await parser.parse({ text, buffer: parserBuffer }, { buffer: parserBuffer });
		logger.info('Parsed data', parsed);

		const resolvedDate = resolveReceiptDate(parsed.date, parsed.rawText);
		const stabilizedDate = stabilizeDate(resolvedDate ?? parsed.date, processedAt);
		if (resolvedDate && stabilizedDate && resolvedDate !== stabilizedDate) {
			logger.info('Stabilized receipt date', {
				extracted: resolvedDate,
				stabilized: stabilizedDate,
			});
		}
		const finalDate = stabilizedDate ?? resolvedDate ?? parsed.date ?? null;
		const companyName = sanitizeCompanyName(parsed.vendor, parsed.rawText);
		const documentType = normalizeDocumentType(parsed.documentType);
		const documentNumber = normalizeDocumentNumber(parsed.documentNumber, parsed.rawText);
		const amountValue = parsed.total != null ? String(parsed.total) : '';
		const currencyValue = parsed.currency ?? '';

		if (from) {
			const latest = getSession(from);
			if (latest?.lastMediaSid && mediaSid && latest.lastMediaSid !== mediaSid) {
				logger.info('Skipping stale receipt job after parsing', {
					jobId: job.id,
					lastJobId: latest.lastJobId,
					lastMediaSid: latest.lastMediaSid,
					mediaSid,
					from,
				});
				return;
			}
			if (latest?.lastJobId && latest.lastJobId !== job.id) {
				logger.info('Skipping stale receipt job after parsing', {
					jobId: job.id,
					lastJobId: latest.lastJobId,
					from,
				});
				return;
			}
		}

		if (!finalDate && from) {
			if (!job.payload?.mediaUrl) {
				throw new Error('Missing media URL');
			}
			storePendingReceiptData(
				from,
				{
					company: companyName,
					taxId: sanitizeTaxId(parsed.taxId),
					documentType,
					documentNumber,
					date: '',
					currency: currencyValue,
					amount: amountValue,
				},
				{
					jobId: job.id,
					pendingMedia: {
						mediaUrl: job.payload.mediaUrl,
						mediaSid: job.payload.mediaSid,
						messageSid: job.payload.messageSid,
						mediaContentType: job.payload.mediaContentType,
						filePath: filePath ?? undefined,
					},
				},
			);
			if (filePath) {
				keepTempFile = true;
			}
			try {
				await whatsapp.sendText(
					from,
					'No encontré la fecha del recibo. Por favor envíala en formato DD/MM/AAAA.',
				);
			} catch (sendErr) {
				logger.warn('Failed to request receipt date', { error: (sendErr as Error).message });
			}
			return;
		}

		// send a reply back to the user who sent the receipt
		if (job.payload && job.payload.from) {
			if (!job.payload.mediaUrl) {
				throw new Error('Missing media URL');
			}
			const to = job.payload.from;
			const session: Session = storePendingReceiptForConfirmation(
				to,
				{
					company: companyName,
					taxId: sanitizeTaxId(parsed.taxId),
					documentType,
					documentNumber,
					date: finalDate ?? '',
					currency: currencyValue,
					amount: amountValue,
				},
				{
					jobId: job.id,
					pendingMedia: {
						mediaUrl: job.payload.mediaUrl,
						mediaSid: job.payload.mediaSid,
						messageSid: job.payload.messageSid,
						mediaContentType: job.payload.mediaContentType,
						filePath: filePath ?? undefined,
					},
				},
			);
			if (filePath) {
				keepTempFile = true;
			}
			const summaryMessage = formatSummary(session);
			const confirmationTemplate = env.TWILIO_CONTENT_SID_CONFIRMATION;
			const latest = getSession(to);
			if (latest?.lastMediaSid && mediaSid && latest.lastMediaSid !== mediaSid) {
				logger.info('Skipping stale confirmation message', {
					jobId: job.id,
					lastJobId: latest.lastJobId,
					lastMediaSid: latest.lastMediaSid,
					mediaSid,
					to,
				});
				return;
			}
			if (latest?.lastJobId && latest.lastJobId !== job.id) {
				logger.info('Skipping stale confirmation message', {
					jobId: job.id,
					lastJobId: latest.lastJobId,
					to,
				});
				return;
			}
			if (latest?.lastConfirmationJobId === job.id) {
				logger.info('Skipping duplicate confirmation message', { jobId: job.id, to });
				return;
			}
			try {
				if (confirmationTemplate) {
					await whatsapp.sendTemplate(to, confirmationTemplate, { '1': summaryMessage });
				} else {
					await whatsapp.sendText(to, summaryMessage);
				}
				markConfirmationSent(to, job.id);
			} catch (e) {
				logger.warn('Failed to send WhatsApp reply (non-fatal in mock mode)', { error: (e as Error).message });
			}
		}
	} catch (err) {
		logger.error('Receipt processing failed', { error: (err as Error).message, job: job.id });
		const attempts = job.attempts ?? 0;
		const nextAttempt = attempts + 1;
		const shouldNotify = nextAttempt >= 3;
		if (!shouldNotify) {
			logger.info('Skipping error notification before retry', {
				jobId: job.id,
				attempt: nextAttempt,
			});
			throw err;
		}
		const to = job.payload?.from;
		if (to) {
			const latest = getSession(to);
			if (latest?.lastMediaSid && mediaSid && latest.lastMediaSid !== mediaSid) {
				logger.info('Skipping stale error message', {
					jobId: job.id,
					lastMediaSid: latest.lastMediaSid,
					mediaSid,
					to,
				});
			} else if (latest?.lastErrorJobId === job.id) {
				logger.info('Skipping duplicate error message', { jobId: job.id, to });
			} else {
				try {
					await whatsapp.sendText(
						to,
						'No pude procesar el recibo. Intenta enviarlo de nuevo o comparte otra foto más clara.',
					);
					markErrorSent(to, job.id);
				} catch (sendErr) {
					logger.warn('Failed to notify user about processing error', { error: (sendErr as Error).message });
				}
			}
		}
		throw err;
	} finally {
		// cleanup downloaded file
		if (filePath && !keepTempFile) {
			try { fs.unlinkSync(filePath); } catch (e) { /* ignore */ }
		}
	}
	}

export default processReceipt;
