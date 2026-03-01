import express from 'express';
import whatsappWebhookRouter from './routes/whatsappWebhook.js';
import healthRouter from './routes/health.js';
import deadletterRouter from './routes/deadletter.js';
import { errorHandler } from './middlewares/errorHandler.js';
import { validateSignature } from './middlewares/validateSignature.js';

const app = express();

// request parsers (Twilio sends x-www-form-urlencoded payloads)
app.use(
  express.urlencoded({
    extended: false,
    verify: (req, _res, buf) => {
      (req as any).rawBody = buf.toString('utf8');
    },
  }),
);
app.use(express.json());

// health route
app.use('/health', healthRouter);

// dead-letter inspection
app.use('/deadletter', deadletterRouter);

// webhook - apply a simple signature check middleware before the webhook
app.use(['/webhook', '/twilio-webhook'], validateSignature, whatsappWebhookRouter);

// simple test route
app.get('/test', (req, res) => {
  res.send('Test route works!');
});

// error handler (must be after all routes)
app.use(errorHandler);

export default app;
