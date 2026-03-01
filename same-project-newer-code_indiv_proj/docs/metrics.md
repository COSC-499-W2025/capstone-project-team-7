# Parser metrics and next steps

Last run (automated, local fixtures):

- Parsed files: 6
- Vendor accuracy: 83.3%
- Date accuracy: 66.7%
- Total accuracy: 83.3%
- Currency accuracy: 83.3%
- Items count accuracy: 66.7%

Notes and recommended next steps:

1. Add more labeled receipts covering varied templates (grocery, pharmacy, restaurants).
2. Expand label schema to include tolerances (e.g., total rounding) and optional fields.
3. Improve parser heuristics for date normalization and multi-line vendor headers.
4. Add per-field confidence scores from the parser when possible.

How to run locally:

```bash
node scripts/run_ocr_batch.js   # generate OCR outputs in test/ocr_raw
node scripts/compute_metrics.js
```

Label JSON schema (example):

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

To create templates for all images in `test/receipts/`:

```bash
node scripts/generate_label_template.js
```
