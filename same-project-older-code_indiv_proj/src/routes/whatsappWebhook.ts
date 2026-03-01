import { Router, Request, Response } from 'express';
import { v4 as uuidv4 } from 'uuid';
import { defaultQueue } from '../../queue/index.js';
import { logger } from '../services/logger';
import whatsapp from '../services/whatsapp';
import { sheets } from '../services/index.js';
import {
	getSession,
	resetForGreeting,
	setStage,
	setPendingField,
	setLastJobId,
	applyFieldUpdate,
	formatSummary,
	formatFieldLines,
	formatFieldSelection,
	resolveFieldBySelection,
	getFieldLabel,
	markSheetAppended,
	type Session,
} from '../conversation/sessionStore.js';
import SHEET_HEADERS from '../config/sheetHeaders.js';
import { env } from '../config/runtimeEnv';

const router = Router();

router.get('/', (req: Request, res: Response) => {
	res.status(200).send('Twilio WhatsApp webhook is active');
});

function normalizeForMatch(value: string) {
	return value
		.toLowerCase()
		.normalize('NFD')
		.replace(/[\u0300-\u036f]/g, '');
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
	return `${base.getFullYear()}-${String(base.getMonth() + 1).padStart(2, '0')}`;
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

	const lines = ['¡Recibo guardado!', ...formatFieldLines(session), '', 'Enlaces:', `Imagen en Drive: ${fileLink}`];
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
		const listTitle = (req.body.ListTitle || '') as string;
		const listId = (req.body.ListId || '') as string;
		const interactiveText = [buttonText, listTitle, listId].find((value) => value && value.trim()) || '';
		const inboundText = (interactiveText || textBody).toString();

		if (!from) {
			logger.warn('Missing From field in Twilio payload', { body: req.body });
			res.status(400).json({ error: 'Missing From' });
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
				defaultQueue.enqueue(job as any);
				setLastJobId(from, job.id);
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
			if (
				normalizedNoAccents === 'yes' ||
				normalizedNoAccents === 'y' ||
				normalizedNoAccents === 'si' ||
				normalizedNoAccents === 's'
			) {
				res.status(200).json({ ack: true });
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

			if (normalizedNoAccents === 'no' || normalizedNoAccents === 'n') {
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
