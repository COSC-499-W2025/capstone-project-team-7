import fs from 'fs';
import path from 'path';
import { Router, Request, Response } from 'express';
import { v4 as uuidv4 } from 'uuid';
import { defaultQueue } from '../../queue/index.js';
import { logger } from '../services/logger';
import whatsapp from '../services/whatsapp';
import { drive, sheets } from '../services/index.js';
import {
	getSession,
	resetForGreeting,
	setStage,
	setPendingField,
	setLastReceiptMeta,
	applyFieldUpdate,
	storeReceiptData,
	formatSummary,
	formatFieldLines,
	formatFieldSelection,
	resolveFieldBySelection,
	getFieldLabel,
	markSheetAppended,
	type Session,
} from '../conversation/sessionStore.js';
import {
	resolveCompanySelection,
	formatCompanySelectionPrompt,
	isCompanyConfigured,
	type CompanyConfig,
} from '../config/companyConfig.js';
import SHEET_HEADERS from '../config/sheetHeaders.js';
import { env } from '../config/runtimeEnv';

const router = Router();

router.get('/', (req: Request, res: Response) => {
	res.status(200).send('Twilio WhatsApp webhook is active');
});

const confirmValues = new Set([
	'yes',
	'y',
	'si',
	's',
	'boton_si',
	'confirm',
	'confirmar',
	'confirmo',
	'ok',
	'listo',
	'aceptar',
	'guardar',
]);

const editValues = new Set([
	'no',
	'n',
	'boton_no',
	'editar',
	'edit',
	'cambiar',
	'cambio',
	'corregir',
	'modificar',
	'rechazar',
]);

function normalizeForMatch(value: string) {
	return value
		.toLowerCase()
		.normalize('NFD')
		.replace(/[\u0300-\u036f]/g, '')
		.trim();
}

function isConfirmReply(value: string) {
	return confirmValues.has(normalizeForMatch(value));
}

function isEditReply(value: string) {
	return editValues.has(normalizeForMatch(value));
}

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

function pad(value: number) {
	return String(value).padStart(2, '0');
}

function formatIsoDate(date: Date) {
	return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

function formatDateForSlug(date: Date) {
	return `${date.getFullYear()}${pad(date.getMonth() + 1)}${pad(date.getDate())}`;
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

function buildReceiptFilenameFromFields(
	fields: Partial<Record<string, string>>,
	receiptDate: Date,
	extension: string,
	fallbackId: string,
) {
	const companySlug = slugify(fields.company) ?? 'recibo';
	const documentSlug = slugify(fields.documentNumber) ?? 'sin-documento';
	const dateSlug = formatDateForSlug(receiptDate);
	const base = `${companySlug}-${documentSlug}-${dateSlug}`;
	const trimmed = base.slice(0, 80) || fallbackId;
	return `${trimmed}${extension}`;
}

async function loadPendingMediaBuffer(pending: Session['pendingMedia']) {
	if (!pending) {
		throw new Error('Missing pending media data');
	}
	let filePath = pending.filePath ?? null;
	if (filePath) {
		try {
			const buffer = fs.readFileSync(filePath);
			return { buffer, filePath };
		} catch (_err) {
			filePath = null;
		}
	}
	if (!pending.mediaUrl) {
		throw new Error('Missing media URL');
	}
	try {
		const downloaded = await whatsapp.downloadMedia(pending.mediaUrl, {
			messageSid: pending.messageSid ?? undefined,
			mediaSid: pending.mediaSid ?? undefined,
			contentType: pending.mediaContentType ?? undefined,
		});
		const buffer = fs.readFileSync(downloaded);
		return { buffer, filePath: downloaded };
	} catch (err) {
		logger.warn('Twilio download failed, trying unauthenticated fetch', {
			error: (err as Error).message,
		});
		const res = await fetch(pending.mediaUrl);
		if (!res.ok) {
			throw new Error(`media fetch failed ${res.status}`);
		}
		const buffer = Buffer.from(await res.arrayBuffer());
		return { buffer, filePath: null };
	}

}

async function finalizePendingReceipt(
	from: string,
	session: Session,
	updatedFields: Partial<Record<string, string>>,
	receiptDate: Date,
	company: CompanyConfig,
) {
	const pending = session.pendingMedia;
	if (!pending) return session;
	const spreadsheetId = company.spreadsheetId;
	if (!spreadsheetId) {
		throw new Error(`Missing spreadsheet id for ${company.name}`);
	}
	const { buffer, filePath } = await loadPendingMediaBuffer(pending);
	const extension = resolveFileExtension(filePath, pending.mediaContentType ?? null);
	const filename = buildReceiptFilenameFromFields(
		updatedFields,
		receiptDate,
		extension,
		session.lastJobId ?? 'recibo',
	);
	const monthFolder = `${pad(receiptDate.getMonth() + 1)}-${receiptDate.getFullYear()}`;
	const uploaded = await drive.upload(buffer, filename, {
		subfolderName: monthFolder,
		parentFolderId: company.driveFolderId,
	});
	if (filePath) {
		try {
			fs.unlinkSync(filePath);
		} catch (_err) {
			// ignore cleanup errors
		}
	}
	const folderId = uploaded.folderId ?? company.driveFolderId;
	const folderUrl = folderId ? `https://drive.google.com/drive/folders/${folderId}` : undefined;
	return storeReceiptData(from, updatedFields, {
		jobId: session.lastJobId ?? undefined,
		driveFile: {
			id: uploaded.id ?? null,
			url: uploaded.url,
			filename,
		},
		sheet: {
			spreadsheetId,
		},
		links: {
			sheetUrl: `https://docs.google.com/spreadsheets/d/${spreadsheetId}`,
			folderUrl,
		},
		companySelection: {
			key: company.key,
			name: company.name,
		},
	});
}

async function sendWhatsAppMessage(to: string, message: string) {
	try {
		await whatsapp.sendText(to, message);
	} catch (err) {
		logger.warn('Failed to send WhatsApp message', { error: (err as Error).message });
	}
}

type ContentVariables = Record<string, string>;

async function sendWhatsAppTemplate(to: string, contentSid: string, variables?: ContentVariables) {
	try {
		await whatsapp.sendTemplate(to, contentSid, variables);
	} catch (err) {
		logger.warn('Failed to send WhatsApp template', { error: (err as Error).message, contentSid });
	}
}

async function sendConfirmationPrompt(to: string, session: Session) {
	const summary = formatSummary(session);
	if (env.TWILIO_CONTENT_SID_CONFIRMATION) {
		await sendWhatsAppTemplate(to, env.TWILIO_CONTENT_SID_CONFIRMATION, { '1': summary });
		return;
	}
	await sendWhatsAppMessage(to, summary);
}

async function sendFieldSelectionPrompt(to: string, session: Session) {
	if (env.TWILIO_CONTENT_SID_FIELD_SELECTION) {
		await sendWhatsAppTemplate(to, env.TWILIO_CONTENT_SID_FIELD_SELECTION);
		return;
	}
	await sendWhatsAppMessage(to, formatFieldSelection(session));
}

async function sendCompanySelectionPrompt(to: string) {
	if (env.TWILIO_CONTENT_SID_COMPANY_SELECTION) {
		await sendWhatsAppTemplate(to, env.TWILIO_CONTENT_SID_COMPANY_SELECTION);
		return;
	}
	await sendWhatsAppMessage(to, formatCompanySelectionPrompt());
}

function resolveDriveFileLink(session: Session): string {
	const driveFile = session.driveFile;
	if (!driveFile) {
		throw new Error('Missing drive file metadata');
	}
	if (driveFile.id) {
		return `https://drive.google.com/file/d/${driveFile.id}/view`;
	}
	return driveFile.url;
}

function parseSessionDate(value?: string | null): Date | null {
	if (!value) return null;
	const trimmed = value.trim();
	if (!trimmed) return null;
	const iso = Date.parse(trimmed);
	if (!Number.isNaN(iso)) {
		const date = new Date(iso);
		if (!Number.isNaN(date.getTime())) {
			return date;
		}
	}
	const match = trimmed.match(/^(\d{1,2})[./-](\d{1,2})[./-](\d{2,4})$/);
	if (match) {
		const day = Number.parseInt(match[1], 10);
		const month = Number.parseInt(match[2], 10);
		let year = Number.parseInt(match[3], 10);
		if (match[3].length === 2) {
			const currentYear = new Date().getFullYear();
			const century = Math.floor(currentYear / 100) * 100;
			year += century;
		}
		if (
			Number.isFinite(day) &&
			Number.isFinite(month) &&
			Number.isFinite(year) &&
			month >= 1 &&
			month <= 12 &&
			day >= 1 &&
			day <= 31
		) {
			const date = new Date(year, month - 1, day);
			if (!Number.isNaN(date.getTime())) {
				return date;
			}
		}
	}
	return null;
}

function deriveSheetName(session: Session): string {
	const parsed = parseSessionDate(session.fields.date);
	const base = parsed ?? new Date();
	return `${String(base.getMonth() + 1).padStart(2, '0')}-${base.getFullYear()}`;
}

async function ensureSheetAppended(userId: string, session: Session): Promise<Session> {
	if (!session.sheet?.spreadsheetId) {
		throw new Error('Missing spreadsheet id in session');
	}
	if (session.sheet.appended) {
		return session;
	}
	const fileLink = resolveDriveFileLink(session);
	const row = [
		session.fields.company || '',
		session.fields.taxId || '',
		session.fields.documentType || '',
		session.fields.documentNumber || '',
		session.fields.date || '',
		session.fields.currency || '',
		session.fields.amount || '',
		{
			hyperlink: {
				url: fileLink,
				label: session.driveFile?.filename || 'recibo',
			},
		},
	];
	const sheetName = deriveSheetName(session);
	await sheets.appendRow(session.sheet.spreadsheetId, row, {
		sheetName,
		headerValues: SHEET_HEADERS,
	});
	return markSheetAppended(userId);
}

function buildFinalConfirmationMessage(session: Session): string {
	const fileLink = resolveDriveFileLink(session);
	const sheetId = session.sheet?.spreadsheetId;
	const sheetUrl =
		session.links?.sheetUrl ||
		(sheetId ? `https://docs.google.com/spreadsheets/d/${sheetId}` : null);
	const folderUrl = session.links?.folderUrl || null;

	const lines = ['¡Recibo guardado!', ...formatFieldLines(session)];
	if (session.selectedCompanyName) {
		lines.push(`Empresa destino: ${session.selectedCompanyName}`);
	}
	lines.push('', 'Enlaces:', `Imagen en Drive: ${fileLink}`);
	if (sheetUrl) {
		lines.push(`Hoja de cálculo: ${sheetUrl}`);
	}
	if (folderUrl) {
		lines.push(`Carpeta de recibos: ${folderUrl}`);
	}
	lines.push('', 'Escribe HOLA cuando quieras procesar otro.');
	return lines.join('\n');
}

router.post('/', async (req: Request, res: Response) => {
	logger.info('Twilio webhook POST received', { body: req.body });
	try {
		const from = req.body.From as string | undefined;
		const messageSid = (req.body.MessageSid || req.body.SmsMessageSid) as string | undefined;
		const numMedia = parseInt(req.body.NumMedia || '0', 10);
		const textBody = (req.body.Body || '').toString();
		const buttonText = (req.body.ButtonText || '') as string;
		const buttonPayload = (req.body.ButtonPayload || '') as string;
		const listTitle = (req.body.ListTitle || '') as string;
		const listId = (req.body.ListId || '') as string;
		const interactiveText = [buttonPayload, buttonText, listTitle, listId].find((value) => value && value.trim()) || '';
		const inboundText = (interactiveText || textBody).toString();

		if (!from) {
			logger.warn('Missing From field in Twilio payload', { body: req.body });
			res.status(400).json({ error: 'Missing From' });
			return;
		}

		if (env.WHATSAPP_ALLOWED_NUMBERS.length > 0 && !env.WHATSAPP_ALLOWED_NUMBERS.includes(from)) {
			logger.info('Skipping message from non-allowlisted number', { from });
			res.status(200).json({ ack: true });
			return;
		}

		const trimmedText = inboundText.trim();
		const normalizedText = trimmedText.toLowerCase();
		const normalizedNoAccents = normalizeForMatch(trimmedText);
		let session = getSession(from);

		if (Number.isInteger(numMedia) && numMedia > 0) {
			const mediaUrl = req.body.MediaUrl0 as string | undefined;
			const mediaContentType = req.body.MediaContentType0 as string | undefined;
			const mediaSid = req.body.MediaSid0 as string | undefined;

			if (!mediaUrl) {
				res.status(400).json({ error: 'Media URL missing' });
				return;
			}

			if (session?.lastMediaSid && mediaSid && session.lastMediaSid === mediaSid) {
				res.status(200).json({ ack: true, duplicate: true });
				return;
			}

			const job = {
				id: uuidv4(),
				payload: {
					type: 'processReceipt',
					from,
					messageSid,
					mediaUrl,
					mediaSid,
					mediaContentType,
				},
			};
			try {
				setLastReceiptMeta(from, job.id, mediaSid, messageSid);
				defaultQueue.enqueue(job as any);
				setStage(from, 'processing');
				res.status(202).json({ ack: true, jobId: job.id });
				await sendWhatsAppMessage(
					from,
					'¡Gracias! Estoy procesando tu recibo. Te avisaré en cuanto tenga el resumen listo.',
				);
			} catch (err) {
				logger.error('Failed to enqueue receipt job', { error: (err as Error).message });
				res.status(500).json({ error: 'processing_failed' });
				await sendWhatsAppMessage(
					from,
					'No pude iniciar el procesamiento del recibo. Intenta reenviar la foto en unos segundos.',
				);
			}
			return;
		}

		if (!trimmedText) {
			res.status(200).json({ ack: true });
			return;
		}

		if (['hello', 'hi', 'hola', 'buenas'].includes(normalizedNoAccents)) {
			session = resetForGreeting(from);
			res.status(200).json({ ack: true });
			await sendWhatsAppMessage(
				from,
				'¡Hola! Envíame la foto de tu recibo y yo me encargo del resto.',
			);
			return;
		}

		if (normalizedNoAccents === 'help' || normalizedNoAccents === 'ayuda') {
			res.status(200).json({ ack: true });
			await sendWhatsAppMessage(
				from,
				'Escribe HOLA para comenzar y luego envía una foto del recibo.\nCuando lo procese podrás responder SI para confirmar o NO para editar datos.',
			);
			return;
		}

		// If no session yet, ask the user to start with hello
		if (!session) {
			res.status(200).json({ ack: true });
			await sendWhatsAppMessage(from, 'Para iniciar responde HOLA y envía la foto del recibo.');
			return;
		}

		if (session.stage === 'processing') {
			res.status(200).json({ ack: true });
			await sendWhatsAppMessage(from, 'Sigo procesando tu recibo, te escribo en cuanto termine.');
			return;
		}

		if (session.stage === 'awaiting_image') {
			res.status(200).json({ ack: true });
			await sendWhatsAppMessage(from, 'Cuando quieras, envíame la foto del recibo.');
			return;
		}

		if (session.stage === 'awaiting_confirmation') {
			if (isConfirmReply(trimmedText)) {
				res.status(200).json({ ack: true });
				if (session.pendingMedia) {
					session = setStage(from, 'awaiting_company_selection');
					await sendCompanySelectionPrompt(from);
					return;
				}
				try {
					session = await ensureSheetAppended(from, session);
					const finalMessage = buildFinalConfirmationMessage(session);
					await sendWhatsAppMessage(from, finalMessage);
					resetForGreeting(from);
				} catch (err) {
					logger.error('Failed to finalize receipt', { error: (err as Error).message });
					await sendWhatsAppMessage(
						from,
						'Hubo un problema al guardar el recibo. Intenta responder SI de nuevo en unos segundos.',
					);
				}
				return;
			}

			if (isEditReply(trimmedText)) {
				session = setStage(from, 'awaiting_field_selection');
				res.status(200).json({ ack: true });
				await sendFieldSelectionPrompt(from, session);
				return;
			}

			res.status(200).json({ ack: true });
			if (env.TWILIO_CONTENT_SID_CONFIRMATION) {
				await sendWhatsAppTemplate(from, env.TWILIO_CONTENT_SID_CONFIRMATION, { '1': formatSummary(session) });
				return;
			}
			await sendWhatsAppMessage(
				from,
				'Responde SI para confirmar el recibo o NO si necesitas hacer cambios.',
			);
			return;
		}

		if (session.stage === 'awaiting_company_selection') {
			if (normalizedNoAccents === 'cancel' || normalizedNoAccents === 'cancelar') {
				res.status(200).json({ ack: true });
				session = setStage(from, 'awaiting_confirmation');
				await sendConfirmationPrompt(from, session);
				return;
			}

			const selectedCompany = resolveCompanySelection(trimmedText);
			if (!selectedCompany) {
				res.status(200).json({ ack: true });
				await sendCompanySelectionPrompt(from);
				return;
			}

			if (!isCompanyConfigured(selectedCompany)) {
				logger.error('Selected company missing config', {
					company: selectedCompany.key,
					spreadsheetId: selectedCompany.spreadsheetId,
					driveFolderId: selectedCompany.driveFolderId,
				});
				res.status(200).json({ ack: true });
				await sendWhatsAppMessage(
					from,
					'Esta empresa no está configurada todavía. Avísame para completar la configuración.',
				);
				return;
			}

			if (!session.pendingMedia) {
				res.status(200).json({ ack: true });
				await sendWhatsAppMessage(
					from,
					'No encontré la imagen pendiente. Envíame nuevamente el recibo para continuar.',
				);
				resetForGreeting(from);
				return;
			}

			const receiptDate = parseSessionDate(session.fields.date) ?? new Date();
			res.status(200).json({ ack: true });
			try {
				session = await finalizePendingReceipt(from, session, session.fields, receiptDate, selectedCompany);
				session = await ensureSheetAppended(from, session);
				const finalMessage = buildFinalConfirmationMessage(session);
				await sendWhatsAppMessage(from, finalMessage);
				resetForGreeting(from);
			} catch (err) {
				logger.error('Failed to finalize receipt after company selection', {
					error: (err as Error).message,
				});
				await sendWhatsAppMessage(
					from,
					'Hubo un problema al guardar el recibo. Intenta responder de nuevo en unos segundos.',
				);
			}
			return;
		}

		if (session.stage === 'awaiting_field_selection') {
			if (normalizedNoAccents === 'cancel' || normalizedNoAccents === 'cancelar') {
				setPendingField(from, null);
				session = setStage(from, 'awaiting_confirmation');
				res.status(200).json({ ack: true });
				await sendConfirmationPrompt(from, session);
				return;
			}

			const selectedField = resolveFieldBySelection(normalizedText);
			if (!selectedField) {
				res.status(200).json({ ack: true });
				await sendFieldSelectionPrompt(from, session);
				return;
			}

			setPendingField(from, selectedField);
			session = setStage(from, 'awaiting_field_value');
			res.status(200).json({ ack: true });
			await sendWhatsAppMessage(
				from,
				`Entendido. Escríbeme el nuevo valor para ${getFieldLabel(selectedField)}.`,
			);
			return;
		}

		if (session.stage === 'awaiting_field_value') {
			if (normalizedNoAccents === 'cancel' || normalizedNoAccents === 'cancelar') {
				if (session.pendingField === 'date' && session.pendingMedia) {
					res.status(200).json({ ack: true });
					await sendWhatsAppMessage(
						from,
						'Necesito la fecha del recibo para continuar. Envíala en formato DD/MM/AAAA.',
					);
					return;
				}
				setPendingField(from, null);
				session = setStage(from, 'awaiting_confirmation');
				res.status(200).json({ ack: true });
				await sendConfirmationPrompt(from, session);
				return;
			}

			if (!session.pendingField) {
				session = setStage(from, 'awaiting_confirmation');
				res.status(200).json({ ack: true });
				await sendConfirmationPrompt(from, session);
				return;
			}

			if (session.pendingField === 'date' && session.pendingMedia) {
				const parsedDate = parseSessionDate(trimmedText);
				if (!parsedDate) {
					res.status(200).json({ ack: true });
					await sendWhatsAppMessage(
						from,
						'No reconocí la fecha. Envíala en formato DD/MM/AAAA, por favor.',
					);
					return;
				}
				const isoDate = formatIsoDate(parsedDate);
				applyFieldUpdate(from, 'date', isoDate);
				setPendingField(from, null);
				session = setStage(from, 'awaiting_confirmation');
				res.status(200).json({ ack: true });
				await sendConfirmationPrompt(from, session);
				return;
			}

			applyFieldUpdate(from, session.pendingField, trimmedText);
			setPendingField(from, null);
			session = setStage(from, 'awaiting_confirmation');
			res.status(200).json({ ack: true });
			await sendConfirmationPrompt(from, session);
			return;
		}

		res.status(200).json({ ack: true });
	} catch (e) {
		logger.error('Twilio webhook handling error', e);
		const from = (req.body?.From as string | undefined) || null;
		if (from) {
			await sendWhatsAppMessage(
				from,
				'Hubo un problema inesperado. Intenta enviar el mensaje de nuevo en unos momentos.',
			);
		}
		res.sendStatus(500);
	}
});

export default router;
