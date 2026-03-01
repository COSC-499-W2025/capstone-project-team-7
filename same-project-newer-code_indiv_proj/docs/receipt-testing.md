 # Receipt testing guide

Place sample receipt images (PNG/JPEG/PDF) in `test/receipts/` and expected label JSONs in `test/labels/` using the same base filename.

Quick commands:

```bash
# run OCR on all receipts (writes to test/ocr_raw/)
node scripts/run_ocr_batch.js

# run unit + integration tests (integration skips if USE_MOCK_SERVICES=true)
export USE_MOCK_SERVICES=false  # if real OCR creds are available
npm test
# Receipt testing guide

Place sample receipt images (PNG/JPEG/PDF) in `test/receipts/` and expected label JSONs in `test/labels/` using the same base filename.

Quick commands:

```bash
# run OCR on all receipts (writes to test/ocr_raw/)
node scripts/run_ocr_batch.js

# run unit + integration tests (integration skips if USE_MOCK_SERVICES=true)
export USE_MOCK_SERVICES=false  # if real OCR creds are available
npm test
```

Schema for label JSON (example `test/labels/sample-receipt.json`):

```json
{
	"vendor": "ACME Store",
	"date": "2025-09-01",
	"total": 5.5,
	"currency": "USD",
	"items": [ {"name":"Coffee","qty":1,"price":3.5} ]
}
```

Keep sensitive receipts out of the repo; redact PII before sharing.
