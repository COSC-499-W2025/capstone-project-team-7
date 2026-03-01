import fs from 'fs';
import path from 'path';
import twilio from 'twilio';
import { logger } from './logger';
import { env } from '../config/runtimeEnv';

type DownloadOptions = {
	messageSid?: string | null;
	mediaSid?: string | null;
	contentType?: string | null;
};

let twilioClient: twilio.Twilio | null = null;

function ensureClient() {
	if (!env.TWILIO_ACCOUNT_SID || !env.TWILIO_AUTH_TOKEN) {
		return null;
	}
	if (!twilioClient) {
		twilioClient = twilio(env.TWILIO_ACCOUNT_SID, env.TWILIO_AUTH_TOKEN);
	}
	return twilioClient;
}

function ensureTmpDir() {
	const dir = path.join(process.cwd(), 'tmp');
	if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
	return dir;
}

function guessExtension(contentType?: string | null) {
	if (!contentType) return 'bin';
	if (contentType === 'image/jpeg' || contentType === 'image/jpg') return 'jpg';
	if (contentType === 'image/png') return 'png';
	if (contentType === 'image/heic') return 'heic';
	if (contentType === 'application/pdf') return 'pdf';
	const parts = contentType.split('/');
	return parts[parts.length - 1] || 'bin';
}

export async function downloadMedia(mediaUrl: string, options: DownloadOptions = {}) {
	if (!mediaUrl) throw new Error('Missing Twilio media URL');
	if (!env.TWILIO_ACCOUNT_SID || !env.TWILIO_AUTH_TOKEN) {
		throw new Error('Twilio credentials not configured (TWILIO_ACCOUNT_SID/TWILIO_AUTH_TOKEN)');
	}

	const authHeader = Buffer.from(`${env.TWILIO_ACCOUNT_SID}:${env.TWILIO_AUTH_TOKEN}`).toString('base64');
	const res = await fetch(mediaUrl, {
		headers: {
			Authorization: `Basic ${authHeader}`,
		},
	});
	if (!res.ok) {
		const text = await res.text();
		throw new Error(`Twilio media download failed ${res.status}: ${text}`);
	}

	const buffer = Buffer.from(await res.arrayBuffer());
	const tmpDir = ensureTmpDir();
	const extension = guessExtension(options.contentType || res.headers.get('content-type'));
	const baseName = options.mediaSid || options.messageSid || `media-${Date.now()}`;
	const filePath = path.join(tmpDir, `${baseName}.${extension}`);
	fs.writeFileSync(filePath, buffer);
	logger.info('Downloaded media from Twilio', { mediaUrl, filePath });
	return filePath;
}

function normalizeToWhatsApp(to: string) {
	if (!to) throw new Error('Missing destination number');
	return to.startsWith('whatsapp:') ? to : `whatsapp:${to}`;
}

type ContentVariables = Record<string, string>;

export async function sendText(to: string, text: string) {
	const client = ensureClient();
	if (!client) {
		throw new Error('Twilio client not configured (TWILIO_ACCOUNT_SID/TWILIO_AUTH_TOKEN)');
	}
	if (!env.TWILIO_WHATSAPP_FROM) {
		throw new Error('TWILIO_WHATSAPP_FROM not set');
	}
	const response = await client.messages.create({
		from: normalizeToWhatsApp(env.TWILIO_WHATSAPP_FROM),
		to: normalizeToWhatsApp(to),
		body: text,
	});
	logger.info('Sent WhatsApp message via Twilio', { to: response.to, sid: response.sid });
	return response;
}

export async function sendTemplate(
	to: string,
	contentSid: string,
	contentVariables?: ContentVariables,
) {
	const client = ensureClient();
	if (!client) {
		throw new Error('Twilio client not configured (TWILIO_ACCOUNT_SID/TWILIO_AUTH_TOKEN)');
	}
	if (!env.TWILIO_WHATSAPP_FROM) {
		throw new Error('TWILIO_WHATSAPP_FROM not set');
	}
	const response = await client.messages.create({
		from: normalizeToWhatsApp(env.TWILIO_WHATSAPP_FROM),
		to: normalizeToWhatsApp(to),
		contentSid,
		contentVariables: contentVariables ? JSON.stringify(contentVariables) : undefined,
	});
	logger.info('Sent WhatsApp template via Twilio', { to: response.to, sid: response.sid, contentSid });
	return response;
}

export default { downloadMedia, sendText, sendTemplate };
