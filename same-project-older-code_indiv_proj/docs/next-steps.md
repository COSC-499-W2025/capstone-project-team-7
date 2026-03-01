# Next steps — what to do now

This file lists the concrete, copy-paste actions you can take right now to finish wiring Google Drive/Sheets for real uploads, test the integration, and secure credentials.

## Quick status (what we already implemented)
- Express app, in-memory queue, worker, dead-letter persistence and admin endpoints.
- WhatsApp ingestion via Twilio sandbox/WhatsApp Business API (signature verification + media download).
- Mock services and "real" stubs for Drive/Sheets that use service-account JSON (raw or base64) via `GOOGLE_SERVICE_ACCOUNT_JSON` / `GOOGLE_SERVICE_ACCOUNT_B64` (preferred)
- A one-shot test script: `scripts/test_google.ts` (appends a row and uploads a tiny file).
- Production parser uses OpenAI (set `OPENAI_API_KEY` and optionally `OPENAI_MODEL`).

## Twilio WhatsApp checklist
1. In Twilio Console, enable the WhatsApp sandbox (or production sender) and note:
   - `TWILIO_ACCOUNT_SID`
   - `TWILIO_AUTH_TOKEN`
   - `TWILIO_WHATSAPP_FROM` (e.g. `whatsapp:+14155238886` for the sandbox number).
2. Point the WhatsApp sandbox "WHEN A MESSAGE COMES IN" webhook to your deployed URL: `https://<your-domain>/webhook`.
3. Export the credentials locally (matching the README example). If Twilio signature verification fails because you are behind an ngrok/cloud proxy, set `TWILIO_WEBHOOK_URL` to the exact public URL Twilio reaches.
4. Start the server (`npm run dev`), join the sandbox, and send an image; you should receive logs about the queued job followed by Drive/Sheets writes once the worker finishes.
5. Ensure `OPENAI_API_KEY` is set so the parser can extract structured data from images.

## Goal: get a working local integration (recommended path)
Use a Google Cloud service account so the worker can call Drive/Sheets without any interactive consent. These steps assume you control (or can share) the target spreadsheet and Drive folder.

### 1) Enable required APIs
In the Google Cloud project that owns your spreadsheet/Drive data enable:
- Google Sheets API
- Google Drive API

Console links (replace project selector if needed):
- Sheets: https://console.developers.google.com/apis/api/sheets.googleapis.com/overview
- Drive:  https://console.developers.google.com/apis/api/drive.googleapis.com/overview

### 2) Create a service account + key
1. Cloud Console → IAM & Admin → Service Accounts → Create Service Account.
2. Grant it basic roles (Editor is fine) and create a JSON key.
3. Base64-encode the JSON for local development:
   ```bash
   export GOOGLE_SERVICE_ACCOUNT_B64="$(base64 < /path/to/key.json | tr -d '\n')"
   ```
   (Or set `GOOGLE_SERVICE_ACCOUNT_JSON` to the raw JSON string in production secrets.)

### 3) Share your spreadsheet and Drive folder
- Add the service account email (looks like `<name>@<project>.iam.gserviceaccount.com`) as an Editor on the spreadsheet referenced by `SPREADSHEET_ID`.
- Share the Drive folder referenced by `DRIVE_UPLOAD_FOLDER_ID` (or a parent Shared drive) with the service account so it can upload files and create subfolders.

### 4) Export env vars and run locally
```bash
export USE_MOCK_SERVICES=false
export SPREADSHEET_ID="<YOUR_SPREADSHEET_ID>"
export DRIVE_UPLOAD_FOLDER_ID="<FOLDER_ID>"        # optional but recommended
export GOOGLE_SERVICE_ACCOUNT_B64="<base64-json>"
export OPENAI_API_KEY="<your-openai-key>"
```
Add the usual Twilio/OpenAI vars from the README as well. `SPREADSHEET_ID` is the string from the sheet URL (`https://docs.google.com/spreadsheets/d/<ID>/...`).

### 5) Run the one-shot test (append row + upload file)
```bash
npx ts-node scripts/test_google.ts
```
Expected logs: `Appended test row to spreadsheet` and `Uploaded file to Drive: { id, url }`.

### 6) Test the WhatsApp flow end-to-end
Start the worker (`npm run dev`), send a receipt photo to your sandbox number, and confirm:
- The job is queued and processed.
- A Drive upload appears inside the configured folder (with month subfolders).
- A row is appended to the spreadsheet with parsed data.

## Troubleshooting
- "API not been used in project": enable Sheets/Drive APIs in Cloud Console and wait a few minutes.
- "Service Accounts do not have storage quota": create a Shared drive/folder in Workspace or share an existing folder from your personal Drive with the service account email.
- Permission errors (403): ensure the service account has Editor/Content manager access on the target spreadsheet/folder (share it explicitly if needed).

## Security & housekeeping
- Do NOT commit service-account JSON or base64 strings. Keep them in a secret manager.
- Rotate the service-account key periodically; update the encoded env var when you do.
- Remove exported env vars after testing:
```bash
unset GOOGLE_SERVICE_ACCOUNT_B64 GOOGLE_SERVICE_ACCOUNT_JSON SPREADSHEET_ID DRIVE_UPLOAD_FOLDER_ID \
  TWILIO_ACCOUNT_SID TWILIO_AUTH_TOKEN TWILIO_WHATSAPP_FROM OPENAI_API_KEY
```

## Files & routes added by the codebase
- Drive client (service account only): `src/services/drive.real.ts`
- Sheets client (service account only): `src/services/sheets.real.ts`
- Dead-letter admin routes: `src/routes/deadletter.ts` (protected by `ADMIN_TOKEN`)
- One-shot tester: `scripts/test_google.ts`

## If you want me to do it for you
- I can walk you through creating the service account, enabling APIs, and sharing the spreadsheet/folder (just ask and I’ll prompt each step).
- If you need per-user access instead, let me know and we can explore alternative approaches (e.g., delegated domain-wide auth).

---
Last updated: auto-generated by the local development assistant.
