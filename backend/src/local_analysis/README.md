# Local PDF Analysis Module

This module provides in-house PDF parsing and summarization capabilities without relying on external LLM services. It's designed for users who prioritize privacy and want local processing of their documents.

## Features

### 🔍 PDF Parser (`pdf_parser.py`)

- Extract text content from PDF documents
- Capture document metadata (title, author, creation date, etc.)
- Performance controls (file size, batch size, page limits)
- Batch processing support
- Parse from file paths or raw bytes

### 📝 PDF Summarizer (`pdf_summarizer.py`)

- In-house extractive summarization using TF-IDF
- Keyword extraction with frequencies
- Document statistics (word count, sentence count, etc.)
- Configurable summary length
- Batch processing support

---

## Quick Start

### Installation

```bash
cd backend/src/local_analysis
pip install -r requirements.txt
```

**Required dependency:** `pypdf`

### Basic Usage

```python
from pdf_parser import create_parser
from pdf_summarizer import create_summarizer
from pathlib import Path

# Parse PDF
parser = create_parser()
result = parser.extract_text_from_pdf(Path("document.pdf"))

if result.success:
    print(f"Extracted {result.num_pages} pages")
    
    # Summarize
    summarizer = create_summarizer()
    summary = summarizer.generate_summary(result.text_content, result.file_name)
    
    if summary.success:
        print("Summary:", summary.summary_text)
        print("Keywords:", summary.keywords[:5])
```

### CLI Usage

```bash
# Get PDF info
python pdf_cli.py info document.pdf

# Extract text
python pdf_cli.py parse document.pdf -o output.txt

# Generate summary
python pdf_cli.py summarize document.pdf -s 5

# Batch process
python pdf_cli.py batch ./pdfs/ -o summaries.json
```

See `CLI_REFERENCE.md` for complete CLI documentation.

---

## Configuration

### Parser Configuration

```python
parser = create_parser(
    max_file_size_mb=10.0,           # Max size per file (default: 10 MB)
    max_batch_size=10,               # Max files per batch (default: 10)
    max_total_batch_size_mb=50.0,   # Max total batch size (default: 50 MB)
    max_pages_per_pdf=100            # Max pages per PDF (default: 100)
)
```

### Summarizer Configuration

```python
summarizer = create_summarizer(
    max_summary_sentences=5,   # Summary length (default: 5)
    min_sentence_length=10,    # Min words per sentence (default: 10)
    max_sentence_length=50,    # Max words per sentence (default: 50)
    keyword_count=10           # Number of keywords (default: 10)
)
```

---

## Common Use Cases

### Parse Multiple PDFs

```python
pdf_files = [Path("doc1.pdf"), Path("doc2.pdf"), Path("doc3.pdf")]
results = parser.parse_batch(pdf_files)

for result in results:
    if result.success:
        print(f"✓ {result.file_name}: {result.num_pages} pages")
```

### Parse from Uploaded File

```python
# Parse PDF from bytes (useful for file uploads)
with open("document.pdf", "rb") as f:
    pdf_bytes = f.read()

result = parser.parse_from_bytes(pdf_bytes, "document.pdf")
```

### Batch Summarization

```python
# Parse PDFs
parse_results = parser.parse_batch(pdf_files)

# Prepare for summarization
documents = [
    (result.file_name, result.text_content)
    for result in parse_results if result.success
]

# Generate summaries
summaries = summarizer.summarize_batch(documents)
```

---

## Data Structures

### PDFParseResult

```python
@dataclass
class PDFParseResult:
    file_name: str              # PDF file name
    success: bool               # Parsing success flag
    metadata: PDFMetadata       # PDF metadata
    text_content: str           # Extracted text
    num_pages: int             # Number of pages
    file_size_mb: float        # File size in MB
    error_message: str         # Error message if failed
```

### DocumentSummary

```python
@dataclass
class DocumentSummary:
    file_name: str                    # Source file name
    summary_text: str                 # Generated summary
    key_points: List[str]            # Key sentences
    keywords: List[Tuple[str, int]]  # (keyword, frequency)
    statistics: Dict[str, Any]       # Document statistics
    success: bool                     # Success flag
    error_message: str               # Error message if failed
```

---

## Error Handling

All functions return result objects with success flags:

```python
result = parser.extract_text_from_pdf(pdf_path)

if not result.success:
    print(f"Error: {result.error_message}")
```

Common errors:
- **File too large**: Exceeds size limits
- **Corrupted PDF**: Cannot be read
- **Invalid format**: Not a valid PDF file
- **Empty content**: PDF contains no extractable text

---

## Privacy & Security

This module is designed with privacy in mind:

- ✅ **No external API calls**: All processing is done locally
- ✅ **No data persistence**: Text is only in memory during processing
- ✅ **No telemetry**: No usage data is sent anywhere
- ✅ **Configurable limits**: Control resource usage

---

## Support

For detailed examples, see `example_usage.py`.  
For CLI commands, see `CLI_REFERENCE.md`.  
For issues, open an issue in the project repository.

