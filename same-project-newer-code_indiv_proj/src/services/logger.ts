// Simple console logger for local development

export class LoggerService {
	info(message: string, meta?: any) {
		console.info('[INFO]', message, meta || '');
	}

	warn(message: string, meta?: any) {
		console.warn('[WARN]', message, meta || '');
	}

	error(message: string, meta?: any) {
		console.error('[ERROR]', message, meta || '');
	}
}

export const logger = new LoggerService();