import { env } from '../config/runtimeEnv.js';

let drive: any;
let ocr: any;
let sheets: any;
let parser: any;

if (env.USE_MOCK_SERVICES) {
  // Force-load TypeScript sources to avoid any stale compiled JS shadowing
  drive = require('./drive.js').default;
  ocr = require('./ocr.js').default;
  sheets = require('./sheets.js').default;
  parser = require('./parser.js').default;
} else {
  // Force-load TypeScript sources to avoid any stale compiled JS shadowing
  drive = require('./drive.real.js').default;
  ocr = require('./ocr.real.js').default;
  sheets = require('./sheets.real.js').default;
  // Prefer real parser; if not available or fails to load, fall back to mock parser
  try {
    parser = require('./parser.real.js').default;
  } catch (e) {
    // eslint-disable-next-line no-console
    console.warn('[services] Falling back to mock parser because real parser failed to load:', (e as Error).message);
    parser = require('./parser.js').default;
  }
}

export { drive, ocr, sheets, parser };

export default { drive, ocr, sheets, parser };

export async function healthCheck() {
  const result: any = { ok: true, services: {} };
  if (env.USE_MOCK_SERVICES) {
    result.services.drive = { status: 'mock' };
    result.services.ocr = { status: 'mock' };
    result.services.sheets = { status: 'mock' };
    return result;
  }

  // For real services, perform lightweight checks: verify credentials exist and parseable
  const raw = process.env.GOOGLE_SERVICE_ACCOUNT || process.env.GOOGLE_SERVICE_ACCOUNT_JSON || process.env.GOOGLE_SERVICE_ACCOUNT_B64;
  if (!raw) {
    result.ok = false;
    result.services.drive = { status: 'missing_credentials' };
    result.services.sheets = { status: 'missing_credentials' };
    return result;
  }

  try {
    JSON.parse(raw);
    result.services.drive = { status: 'credentials_ok' };
    result.services.sheets = { status: 'credentials_ok' };
  } catch (e) {
    result.ok = false;
    result.services.drive = { status: 'invalid_credentials', error: String(e) };
    result.services.sheets = { status: 'invalid_credentials', error: String(e) };
  }

  return result;
}
