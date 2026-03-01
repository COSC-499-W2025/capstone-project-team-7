# Ankas Agent

Small Express + TypeScript app that processes receipts through a worker pipeline.

Features

- In-memory queue with retry and dead-letter persistence
- Worker that uploads images to Drive, runs OCR, parses receipts, and appends to Sheets
- OpenAI-powered receipt parser for production workflows
- Twilio WhatsApp webhook + outbound helper for interactive flows
- Mockable services for local development
- Tools to run OCR batches, create label templates, and compute parser metrics

Quick commands

- Run unit tests:

```bash
npm test
```

- Run OCR batch (reads images from `test/receipts/` and writes OCR JSON to `test/ocr_raw/`):

```bash
node scripts/run_ocr_batch.js
```

- Compute parser metrics (compare `test/ocr_raw/` to `test/labels/`):

```bash
node scripts/compute_metrics.js
```

Run locally

```bash
npm install
npm run dev
```

Environment variables (summary)

Copy `.env.example` to `.env` and fill values. Key variables used by the project:

- `PORT` (default 3000)
- `USE_MOCK_SERVICES` (true/false) — set to `false` to use real services
- `ADMIN_TOKEN` — admin token for protected endpoints
- `SPREADSHEET_ID` — Google Sheets ID used by the app
- `DRIVE_UPLOAD_FOLDER_ID` — Drive folder for uploads
- Twilio credentials:
  - `TWILIO_ACCOUNT_SID`
  - `TWILIO_AUTH_TOKEN`
  - `TWILIO_WHATSAPP_FROM` — the WhatsApp-enabled number (e.g. `whatsapp:+14155238886` for sandbox)
  - `TWILIO_WEBHOOK_URL` (optional override for signature validation when behind proxies)
  - `TWILIO_CONTENT_SID_CONFIRMATION` (optional Content Template for confirmation buttons; body should include `{{1}}` to inject the summary)
  - `TWILIO_CONTENT_SID_FIELD_SELECTION` (optional Content Template for field selection list)
- OpenAI credentials:
  - `OPENAI_API_KEY`
  - `OPENAI_MODEL` (optional, defaults to `gpt-4o-mini`)
- Google credentials:
  - `GOOGLE_SERVICE_ACCOUNT_B64` (base64-encoded JSON)
  - `GOOGLE_SERVICE_ACCOUNT_JSON` (raw JSON string)

Full `.env` example (local development):

```env
USE_MOCK_SERVICES=true
ADMIN_TOKEN=changeme
SPREADSHEET_ID=your_spreadsheet_id_here
DRIVE_UPLOAD_FOLDER_ID=your_drive_folder_id_here
TWILIO_ACCOUNT_SID=ACXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
# TWILIO_WEBHOOK_URL=https://example.com/webhook (set if Twilio signature fails behind a proxy)
# TWILIO_CONTENT_SID_CONFIRMATION=HX... (optional confirmation template, include {{1}} in body)
# TWILIO_CONTENT_SID_FIELD_SELECTION=HX... (optional field selection list template)
OPENAI_API_KEY=sk-your-key
# OPENAI_MODEL=gpt-4o-mini
# GOOGLE_SERVICE_ACCOUNT_B64=... (preferred for local)
```

Label JSON schema

Place label JSON files in `test/labels/` with the same basename as the OCR output JSON. Example (`test/labels/sample-1.json`):

```json
{
  "vendor": "ACME Store",
  "date": "2025-09-10",
  "total": "12.50",
  "currency": "USD",
  "items": [
    { "name": "Coffee", "qty": 1, "price": "2.50" },
    { "name": "Sandwich", "qty": 1, "price": "10.00" }
  ]
}
```

Useful scripts

```bash
# generate placeholder labels for images in test/receipts/
node scripts/generate_label_template.js

# run OCR on images in test/receipts/ (writes JSON to test/ocr_raw/)
node scripts/run_ocr_batch.js

# compute metrics comparing parser output to labels
node scripts/compute_metrics.js
```

Google credentials guide

- Create a service account in GCP and grant Drive/Sheets access.
- Store the JSON securely. For local runs you can set `GOOGLE_SERVICE_ACCOUNT_B64` to the base64 of the JSON file. Example:

  ```bash
  export GOOGLE_SERVICE_ACCOUNT_B64=$(base64 -w0 /path/to/sa.json)
  ```

- The app will prefer `GOOGLE_SERVICE_ACCOUNT_B64` then `GOOGLE_SERVICE_ACCOUNT_JSON`.

Security note: never commit service-account JSON. Use environment variables or a secret manager.
