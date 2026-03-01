import app from './app';
import './workerRunner.js';
import { defaultQueue } from '../queue/index.js';
import { env } from './config/runtimeEnv';

const PORT = process.env.PORT || 3000;

const server = app.listen(PORT, () => {
    console.log(`Server is running on port ${PORT}`);
    console.log('[startup] DEV:', env.DEV, 'USE_MOCK_SERVICES:', env.USE_MOCK_SERVICES);
    console.log('[startup] Twilio env present:', {
        TWILIO_ACCOUNT_SID: Boolean(env.TWILIO_ACCOUNT_SID),
        TWILIO_AUTH_TOKEN: Boolean(env.TWILIO_AUTH_TOKEN),
        TWILIO_WHATSAPP_FROM: env.TWILIO_WHATSAPP_FROM || '(missing)'
    });
    console.log('[startup] process.env TWILIO lengths:', {
        SID: (process.env.TWILIO_ACCOUNT_SID || '').length,
        TOKEN: (process.env.TWILIO_AUTH_TOKEN || '').length,
        FROM: (process.env.TWILIO_WHATSAPP_FROM || '').length,
    });
});

async function shutdown(code = 0) {
    console.log('Shutdown initiated');
    server.close(async () => {
        try {
            await defaultQueue.drain(10000);
            console.log('Queue drained, exiting');
            process.exit(code);
        } catch (err) {
            console.error('Failed to drain queue:', err);
            process.exit(1);
        }
    });
}

process.on('SIGINT', () => shutdown(0));
process.on('SIGTERM', () => shutdown(0));
