import { Request, Response, NextFunction } from 'express';
import twilio from 'twilio';
import { env } from '../config/runtimeEnv';
import { logger } from '../services/logger';

function resolveRequestUrl(req: Request) {
	if (env.TWILIO_WEBHOOK_URL) return env.TWILIO_WEBHOOK_URL;
	const protocol = req.get('x-forwarded-proto') || req.protocol;
	const host = req.get('host');
	return `${protocol}://${host}${req.originalUrl}`;
}

export function validateSignature(req: Request, res: Response, next: NextFunction) {
	if (env.DEV || !env.TWILIO_AUTH_TOKEN) return next();

	const signature = req.headers['x-twilio-signature'] as string | undefined;
	if (!signature) {
		logger.warn('Twilio signature missing');
		return res.sendStatus(401);
	}

	const url = resolveRequestUrl(req);
	const rawBody = (req as any).rawBody as string | undefined;
	const contentType = req.headers['content-type'] || '';
	let valid = false;

	try {
		valid = twilio.validateRequest(env.TWILIO_AUTH_TOKEN, signature, url, req.body || {});
	} catch (err) {
		logger.error('Twilio signature validation threw', { error: (err as Error).message });
		return res.sendStatus(500);
	}

	if (!valid) {
		logger.warn('Twilio signature invalid', {
			expectedUrl: url,
			originalUrl: req.originalUrl,
			host: req.get('host'),
			contentType,
			hasRawBody: Boolean(rawBody),
		});
		return res.sendStatus(403);
	}

	next();
}
