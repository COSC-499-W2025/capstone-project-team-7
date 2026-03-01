import dotenv from 'dotenv';

// Force .env values to override any pre-existing process.env so local .env is authoritative during dev
dotenv.config({ override: true });

// Debug: print presence (not values) of TWILIO_* when DEV to diagnose env loading
if (process.env.DEV === 'true') {
  const twilioKeys = Object.keys(process.env).filter((k) => k.startsWith('TWILIO'));
  // eslint-disable-next-line no-console
  console.log('[env] Detected TWILIO keys in process.env:', twilioKeys);
  // eslint-disable-next-line no-console
  console.log('[env] TWILIO lengths:', {
    SID: (process.env.TWILIO_ACCOUNT_SID || '').length,
    TOKEN: (process.env.TWILIO_AUTH_TOKEN || '').length,
    FROM: (process.env.TWILIO_WHATSAPP_FROM || '').length,
    WEBHOOK_URL: (process.env.TWILIO_WEBHOOK_URL || '').length,
  });
}

const {
  PORT,
  DEV,
  USE_MOCK_SERVICES,
  ADMIN_TOKEN,
  TWILIO_ACCOUNT_SID,
  TWILIO_AUTH_TOKEN,
  TWILIO_WHATSAPP_FROM,
  TWILIO_WEBHOOK_URL,
  OPENAI_API_KEY,
  OPENAI_MODEL,
  SPREADSHEET_ID,
  DRIVE_UPLOAD_FOLDER_ID,
} = process.env;

export const env = {
  PORT: PORT || '3000',
  DEV: DEV === 'true' || false,
  USE_MOCK_SERVICES: USE_MOCK_SERVICES === 'true' || false,
  ADMIN_TOKEN: ADMIN_TOKEN || '',
  TWILIO_ACCOUNT_SID: TWILIO_ACCOUNT_SID || '',
  TWILIO_AUTH_TOKEN: TWILIO_AUTH_TOKEN || '',
  TWILIO_WHATSAPP_FROM: TWILIO_WHATSAPP_FROM || '',
  TWILIO_WEBHOOK_URL: TWILIO_WEBHOOK_URL || '',
  OPENAI_API_KEY: OPENAI_API_KEY || '',
  OPENAI_MODEL: OPENAI_MODEL || 'gpt-4o-mini',
  SPREADSHEET_ID: SPREADSHEET_ID || '',
  DRIVE_UPLOAD_FOLDER_ID: DRIVE_UPLOAD_FOLDER_ID || '',
};

export default env;
// load & validate env vars
