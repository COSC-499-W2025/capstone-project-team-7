# Local Analysis Module

This module provides privacy-first, in-house analysis capabilities for PDFs and documents without relying on external LLM services. All processing is done locally on your machine.

## 📋 Table of Contents
- [Features](#features)
- [Textual Integration](#textual-integration)
- [Quick Start](#quick-start)
- [Supported File Types](#supported-file-types)
- [Configuration](#configuration)
- [Common Use Cases](#common-use-cases)
- [Data Structures](#data-structures)
- [CLI Usage](#cli-usage)
- [Privacy & Security](#privacy--security)
- [Testing](#testing)

---

## Textual Integration

### Automatic PDF Analysis During Portfolio Scans

The PDF analysis module is fully integrated into the Textual workflow (`src/cli/textual_app.py`). When you run a portfolio scan that contains PDF files:

1. **Automatic Detection**: The scanner identifies all PDF files in the scanned directory or archive.
2. **Optional Analysis**: After the scan completes, you're prompted whether to analyze the PDFs.
3. **In-Memory Processing**: PDFs are extracted from the archive (if scanning a .zip) or read directly from the filesystem.
4. **Local Summarization**: Each PDF is parsed and summarized using the in-house TF-IDF based summarizer.
5. **UI Display**: View PDF summaries, statistics, keywords, and key points directly in the terminal.
6. **JSON Export**: All PDF analysis results are included in scan exports for further review.

**Privacy Note**: All PDF processing happens locally on your machine. No data is sent to external services.

### Example Workflow

```bash
# Start the Textual UI
python -m src.cli.textual_app

# Select "Run Portfolio Scan"
# Choose a directory containing PDF files
# After scan completes, select "Yes" to analyze PDFs
# View results in the "View PDF summaries" option
# Export with "Export JSON report" to save all data
```

### Programmatic Usage

```python
from src.local_analysis.pdf_parser import create_parser
from src.local_analysis.pdf_summarizer import create_summarizer

# Parse PDF
parser = create_parser()
result = parser.extract_text_from_pdf(Path("document.pdf"))

# Summarize
summarizer = create_summarizer()
summary = summarizer.generate_summary(result.text_content, result.file_name)

print(f"Summary: {summary.summary_text}")
print(f"Keywords: {summary.keywords[:5]}")
```

---

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

### 🎨 Media Analyzer (`media_analyzer.py`)

- Aggregates metadata from images, audio, and video files
- Computes duration, resolution, bitrate, and aspect-ratio metrics
- Highlights low-resolution images and short-form media clips
- Produces deterministic insights usable when LLM analysis is unavailable
- (New) Generates offline image/video/audio content labels with PyTorch (TorchVision + Torchaudio) so you can see what appears or is mentioned in each asset without external APIs
- (New) Extracts approximate audio tempo (BPM) and genre heuristics using Torchaudio + Librosa so you can tag songs/podcasts quickly
- Accepts `FileMetadata` objects or persisted records with `media_info`
### 📄 Document Analyzer (`document_analyzer.py`)

- **Multiple Format Support**: `.txt`, `.md`, `.markdown`, `.rst`, `.log`, `.docx`
- **Comprehensive Metadata**: Word count, reading time, paragraph count, line count
- **Intelligent Summarization**: Reuses PDF summarizer for consistent results
- **Markdown Features**: Heading extraction, code block detection, link/image counting
- **DOCX Support**: Page count, section detection, heading extraction (optional)
- **Batch Processing**: Analyze multiple documents efficiently
- **Encoding Detection**: Automatic fallback for different character encodings

---

## Quick Start

### Installation

```bash
cd backend/src/local_analysis
pip install -r requirements.txt
```

**Required dependencies:**
- `pypdf` - PDF parsing
- `python-docx` - Optional, for `.docx` support

#### Image/Video Content Insights (optional)

To enable the new computer-vision + audio summaries, install the extra dependencies:

```bash
# From backend/
pip install -r requirements.txt
# or use the extras target
pip install ".[vision]"
```

This pulls in `torch`, `torchvision`, `torchaudio`, and `numpy` so image/video/audio descriptions run entirely on your machine.

### Python API - PDF

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

### Python API - Documents

```python
from document_analyzer import create_analyzer

# Create analyzer
analyzer = create_analyzer()

# Analyze a text/markdown document
result = analyzer.analyze_document(Path("README.md"))

if result.success and result.metadata:
    print(f"Words: {result.metadata.word_count}")
    print(f"Reading time: {result.metadata.reading_time_minutes:.1f} min")
    print(f"Headings: {result.metadata.heading_count}")
    print(f"Summary: {result.summary}")
```

### CLI Usage

```bash
# PDF Commands
python pdf_cli.py info document.pdf
python pdf_cli.py parse document.pdf -o output.txt
python pdf_cli.py summarize document.pdf -s 5
python pdf_cli.py batch ./pdfs/ -o summaries.json

# Document Commands
python document_cli.py info README.md
python document_cli.py analyze document.txt -o output.json
python document_cli.py summarize README.md -s 7
python document_cli.py batch ./docs/ -o summaries.json
```

See `CLI_REFERENCE.md` for complete CLI documentation.

---

## Supported File Types

| Type | Extensions | CLI Tool | Features |
|------|------------|----------|----------|
| **PDF** | `.pdf` | `pdf_cli.py` | Text extraction, metadata, page count |
| **Text** | `.txt` | `document_cli.py` | Basic text analysis, summarization |
| **Markdown** | `.md`, `.markdown` | `document_cli.py` | Headings, code blocks, links, images |
| **ReStructuredText** | `.rst` | `document_cli.py` | Basic text analysis |
| **Log Files** | `.log` | `document_cli.py` | Basic text analysis |
| **Word Documents** | `.docx` | `document_cli.py` | Pages, sections, headings (requires python-docx) |

---

## Configuration

### PDF Parser Configuration

```python
parser = create_parser(
    max_file_size_mb=10.0,           # Max size per file (default: 10 MB)
    max_batch_size=10,               # Max files per batch (default: 10)
    max_total_batch_size_mb=50.0,   # Max total batch size (default: 50 MB)
    max_pages_per_pdf=100            # Max pages per PDF (default: 100)
)
```

### PDF Summarizer Configuration

```python
summarizer = create_summarizer(
    max_summary_sentences=5,   # Summary length (default: 5)
    min_sentence_length=10,    # Min words per sentence (default: 10)
    max_sentence_length=50,    # Max words per sentence (default: 50)
    keyword_count=10           # Number of keywords (default: 10)
)
```

### Document Analyzer Configuration

```python
analyzer = create_analyzer(
    max_file_size_mb=20.0,  # Max file size (default: 10 MB)
    max_batch_size=50,      # Max files per batch (default: 20)
    encoding='utf-8'         # Default encoding (default: utf-8)
)
```

---

## Common Use Cases

### 1. Analyze Multiple Documents

```python
from pathlib import Path

# Analyze all markdown files in a directory
md_files = list(Path("./docs").glob("*.md"))
results = analyzer.analyze_batch(md_files)

for result in results:
    if result.success and result.metadata:
        print(f"✓ {result.file_name}: {result.metadata.word_count} words")
        print(f"  Summary: {result.summary[:100]}...")
```

### 2. Parse PDFs from Uploaded Files

```python
# Parse PDF from bytes (useful for file uploads)
with open("document.pdf", "rb") as f:
    pdf_bytes = f.read()

result = parser.parse_from_bytes(pdf_bytes, "document.pdf")
```

### 3. Batch PDF Summarization

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

### 4. Markdown Feature Extraction

```python
result = analyzer.analyze_document(Path("README.md"))

if result.success and result.metadata:
    print(f"Headings: {result.metadata.heading_count}")
    print(f"Code blocks: {result.metadata.code_blocks}")
    print(f"Links: {result.metadata.links}")
    print(f"Images: {result.metadata.images}")
    
    # Access extracted headings
    for heading in result.metadata.headings:
        print(f"  - {heading}")
```

### 5. Export to JSON

```python
result = analyzer.analyze_document(Path("document.md"))
json_data = analyzer.to_json(result)

# Save to file
import json
with open("analysis.json", "w") as f:
    json.dump(json_data, f, indent=2)
```

### 6. Analyze Text Directly (Without File)

```python
text = "Your document content here..."
result = analyzer.analyze_from_text(text, "my_document")

print(f"Summary: {result.summary}")
print(f"Key topics: {result.key_topics}")
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

### DocumentAnalysisResult

```python
@dataclass
class DocumentAnalysisResult:
    file_name: str              # Document file name
    file_type: str              # File extension
    success: bool               # Analysis success flag
    metadata: DocumentMetadata  # Extracted metadata
    summary: str                # Generated summary
    key_topics: List[str]      # Key topics
    keywords: List[Tuple[str, int]]  # (keyword, frequency)
    statistics: Dict[str, Any] # Document statistics
    file_size_mb: float        # File size in MB
    error_message: str         # Error message if failed
```

### DocumentMetadata

```python
@dataclass
class DocumentMetadata:
    file_type: str                # File extension
    word_count: int               # Total words
    character_count: int          # Total characters
    line_count: int               # Total lines
    paragraph_count: int          # Total paragraphs
    reading_time_minutes: float   # Estimated reading time
    
    # Markdown-specific (optional)
    heading_count: int = 0
    headings: List[str] = []
    code_blocks: int = 0
    links: int = 0
    images: int = 0
    
    # DOCX-specific (optional)
    pages: Optional[int] = None
    sections: Optional[int] = None
```

---

## CLI Usage

### PDF CLI Tool

```bash
# Get PDF information
python pdf_cli.py info document.pdf

# Extract text
python pdf_cli.py parse document.pdf -o output.txt

# Generate summary
python pdf_cli.py summarize document.pdf -s 5 -k 10

# Batch process PDFs
python pdf_cli.py batch ./pdfs/ -o summaries.json
```

### Document CLI Tool

```bash
# Get document information
python document_cli.py info README.md

# Analyze document
python document_cli.py analyze document.txt -o analysis.json

# Generate summary
python document_cli.py summarize README.md -s 7 -k 15

# Batch process documents
python document_cli.py batch ./docs/ -o summaries.json
```

**See `CLI_REFERENCE.md` for complete documentation.**

---

## Error Handling

All functions return result objects with success flags:

```python
result = analyzer.analyze_document(Path("document.txt"))

if not result.success:
    print(f"Error: {result.error_message}")
    # Handle specific errors
    if "Empty document" in result.error_message:
        print("File is empty")
    elif "Unsupported file type" in result.error_message:
        print("File format not supported")
    elif "exceeds limit" in result.error_message:
        print("File too large")
```

### Common Errors

- **File too large**: Exceeds size limits (configurable)
- **Corrupted file**: Cannot be read or parsed
- **Invalid format**: Not a valid file format
- **Empty content**: File contains no extractable text
- **Encoding issues**: Character encoding problems (auto-handled with fallbacks)
- **Missing dependency**: python-docx required for .docx files

---

## Privacy & Security

This module is designed with privacy as a top priority:

- ✅ **No external API calls**: All processing is done locally
- ✅ **No data persistence**: Text is only in memory during processing
- ✅ **No telemetry**: No usage data is sent anywhere
- ✅ **Configurable limits**: Control resource usage
- ✅ **100% Local Processing**: No data leaves your machine
- ✅ **No external dependencies**: Core functionality uses only standard ML libraries

---

## Testing

```bash
# Run all tests
pytest tests/ -v

# Test specific modules
pytest tests/test_document_analyzer.py -v
pytest tests/test_pdf_parser.py -v

# With coverage
pytest tests/ --cov=backend/src/local_analysis --cov-report=term-missing

# Run a specific test
pytest tests/test_document_analyzer.py::TestDocumentAnalyzer::test_analyze_markdown -v
```

---

## Architecture

```
local_analysis/
├── pdf_parser.py              # PDF text extraction
├── pdf_summarizer.py          # Text summarization (shared by PDF and documents)
├── document_analyzer.py       # Document analysis (.txt, .md, .rst, .log)
├── docx_analyzer.py          # DOCX extension (optional)
├── pdf_cli.py                # PDF CLI tool
├── document_cli.py           # Document CLI tool
├── demo_document_analysis.py # Interactive demos
├── README.md                 # This file
└── CLI_REFERENCE.md          # Complete CLI documentation
```

### Design Principles

1. **Consistency**: PDF and document analysis share the same summarization engine
2. **Extensibility**: Easy to add new file format support
3. **Privacy-First**: No external API calls, all processing is local
4. **Error Handling**: Comprehensive error messages and graceful degradation
5. **Testability**: High test coverage (>80% target)

---

## Examples

### Interactive Demos

```bash
# Run document analysis demos
python demo_document_analysis.py
```

The demo includes:
1. Text file analysis
2. Markdown analysis with feature extraction
3. Direct text analysis (no file)
4. Batch processing
5. JSON export
6. Error handling

---

## Roadmap

### Planned Features
- [ ] HTML document support
- [ ] RTF document support
- [ ] ODT (OpenDocument) support
- [ ] Code file analysis (.py, .js, .java, etc.)
- [ ] Git repository analysis
- [ ] Configuration file analysis (package.json, etc.)
- [ ] Multi-language support
- [ ] Readability scores (Flesch-Kincaid, etc.)
- [ ] Sentiment analysis
- [ ] Topic modeling with LDA

---

## Contributing

Contributions welcome! Please ensure:
- All tests pass
- Code coverage remains >80%
- Follow existing code style
- Add tests for new features
- Update documentation

---

## Support

For detailed examples, see `example_usage.py`.  
For CLI commands, see `CLI_REFERENCE.md`.  
For issues, open an issue in the project repository.
- **Demos**: See `demo_document_analysis.py` for interactive examples
- **CLI Reference**: See `CLI_REFERENCE.md` for complete CLI documentation
- **Issues**: Open an issue in the project repository
- **Examples**: Check the `tests/` directory for usage examples

---

## License

See project LICENSE file.
