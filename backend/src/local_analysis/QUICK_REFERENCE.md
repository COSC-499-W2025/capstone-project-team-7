# PDF Analysis Module - Quick Reference

## Installation

```bash
pip install PyPDF2==3.0.1
```

## Quick Start

### Parse a PDF

```python
from pdf_parser import create_parser

parser = create_parser()
result = parser.extract_text_from_pdf(Path("document.pdf"))

if result.success:
    print(result.text_content)
```

### Summarize Text

```python
from pdf_parser import create_summarizer

summarizer = create_summarizer()
summary = summarizer.generate_summary(text, "document.pdf")

if summary.success:
    print(summary.summary_text)
    print(summary.keywords)
```

### Full Pipeline

```python
from pdf_parser import create_parser, create_summarizer
from pathlib import Path

# Initialize
parser = create_parser()
summarizer = create_summarizer()

# Parse
result = parser.extract_text_from_pdf(Path("document.pdf"))

# Summarize
if result.success:
    summary = summarizer.generate_summary(result.text_content, result.file_name)
    print(summary.summary_text)
```

## Configuration Presets

### Strict Mode (Small Files Only)
```python
parser = create_parser(
    max_file_size_mb=2.0,
    max_batch_size=3,
    max_total_batch_size_mb=5.0,
    max_pages_per_pdf=20
)
```

### Standard Mode (Default)
```python
parser = create_parser(
    max_file_size_mb=10.0,
    max_batch_size=10,
    max_total_batch_size_mb=50.0,
    max_pages_per_pdf=100
)
```

### Lenient Mode (Large Files)
```python
parser = create_parser(
    max_file_size_mb=25.0,
    max_batch_size=20,
    max_total_batch_size_mb=100.0,
    max_pages_per_pdf=200
)
```

## Common Patterns

### Process Multiple PDFs

```python
pdf_files = [Path(f) for f in ["doc1.pdf", "doc2.pdf", "doc3.pdf"]]
results = parser.parse_batch(pdf_files)

for result in results:
    if result.success:
        summary = summarizer.generate_summary(result.text_content, result.file_name)
        print(f"{result.file_name}: {summary.summary_text[:100]}...")
```

### Handle Uploaded Files

```python
# From FastAPI
async def process_upload(file: UploadFile):
    pdf_bytes = await file.read()
    result = parser.parse_from_bytes(pdf_bytes, file.filename)
    
    if result.success:
        summary = summarizer.generate_summary(result.text_content, result.file_name)
        return {"summary": summary.summary_text}
```

### Extract Metadata Only

```python
result = parser.extract_text_from_pdf(Path("document.pdf"))
if result.success and result.metadata:
    print(f"Title: {result.metadata.title}")
    print(f"Author: {result.metadata.author}")
    print(f"Pages: {result.metadata.num_pages}")
```

## Performance Tips

1. **Batch Processing**: Use `parse_batch()` for multiple files
2. **Page Limits**: Set `max_pages_per_pdf` to control processing time
3. **File Size**: Reject large files early with size validation
4. **Memory**: Process large batches in chunks

## Error Handling

```python
result = parser.extract_text_from_pdf(path)

if not result.success:
    if "size" in result.error_message.lower():
        # Handle size limit error
        print("File too large")
    elif "read" in result.error_message.lower():
        # Handle PDF read error
        print("Corrupted PDF")
    else:
        # Handle other errors
        print(f"Error: {result.error_message}")
```

## Testing

```bash
# Run tests
cd backend
python -m pytest tests/test_pdf_analysis.py -v

# Run specific test
python -m pytest tests/test_pdf_analysis.py::TestPDFSummarizer::test_generate_summary_with_valid_text -v
```

## Logging

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# Or configure specific logger
logger = logging.getLogger('pdf_parser')
logger.setLevel(logging.INFO)
```

## Data Structures

### Parse Result
```python
result.file_name         # str
result.success           # bool
result.text_content      # str
result.num_pages         # int
result.file_size_mb      # float
result.metadata          # PDFMetadata
result.error_message     # str or None
```

### Summary
```python
summary.file_name        # str
summary.summary_text     # str
summary.key_points       # List[str]
summary.keywords         # List[Tuple[str, int]]
summary.statistics       # Dict[str, Any]
summary.success          # bool
summary.error_message    # str or None
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Import errors | Check Python path and module location |
| Empty text extraction | PDF may be image-based (needs OCR) |
| Memory errors | Reduce file size or page limits |
| Slow processing | Reduce batch size or page limits |
| Poor summaries | Adjust sentence length or count settings |

## Resources

- Full Documentation: `backend/src/local_analysis/README.md`
- Examples: `backend/src/local_analysis/example_usage.py`
- Tests: `tests/test_pdf_analysis.py`
