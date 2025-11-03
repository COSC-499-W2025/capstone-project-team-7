# Local Analysis CLI - Quick Reference

Complete reference for PDF and Document analysis command-line tools.

## Setup

Navigate to the CLI directory:
```bash
cd backend/src/local_analysis
```

---

## PDF Analysis Commands

### 1. Get PDF Info

View PDF metadata and basic information.

```bash
python pdf_cli.py info <pdf-file>
```

**Example:**
```bash
python pdf_cli.py info report.pdf
```

---

### 2. Extract Text from PDF

Extract text from a PDF.

```bash
python pdf_cli.py parse <pdf-file> [options]
```

**Options:**
- `-o <file>` - Save to file (.txt or .json)
- `--show-text` - Display text in console

**Examples:**
```bash
python pdf_cli.py parse document.pdf
python pdf_cli.py parse document.pdf -o output.txt
python pdf_cli.py parse document.pdf -o output.json
```

---

### 3. Summarize PDF

Generate a summary of the PDF content.

```bash
python pdf_cli.py summarize <pdf-file> [options]
```

**Options:**
- `-o <file>` - Save summary to file
- `-s <num>` - Number of sentences (default: 7)
- `-k <num>` - Number of keywords (default: 15)

**Examples:**
```bash
python pdf_cli.py summarize document.pdf
python pdf_cli.py summarize document.pdf -s 5
python pdf_cli.py summarize document.pdf -o summary.json
```

---

### 4. Batch Process PDFs

Process multiple PDFs in a directory.

```bash
python pdf_cli.py batch <directory> [options]
```

**Options:**
- `-o <file>` - Save all summaries to file
- `-s <num>` - Sentences per summary (default: 5)
- `-k <num>` - Keywords per document (default: 10)

**Examples:**
```bash
python pdf_cli.py batch ./pdfs/
python pdf_cli.py batch ./pdfs/ -o summaries.json
```

---

## Document Analysis Commands

### 1. Get Document Info

View document metadata and basic information.

```bash
python document_cli.py info <document-file>
```

**Example:**
```bash
python document_cli.py info README.md
python document_cli.py info document.txt
```

**Supported formats:** `.txt`, `.md`, `.markdown`, `.rst`, `.log`, `.docx`

---

### 2. Analyze Document

Analyze document and extract comprehensive metadata.

```bash
python document_cli.py analyze <document-file> [options]
```

**Options:**
- `-o <file>` - Save to file (.txt or .json)
- `--show-keywords` - Display top keywords
- `--encoding <enc>` - File encoding (default: utf-8)
- `--max-size <MB>` - Maximum file size (default: 20)

**Examples:**
```bash
python document_cli.py analyze document.txt
python document_cli.py analyze README.md -o analysis.json
python document_cli.py analyze document.txt --show-keywords
```

---

### 3. Summarize Document

Generate a summary of the document content.

```bash
python document_cli.py summarize <document-file> [options]
```

**Options:**
- `-o <file>` - Save summary to file
- `-s <num>` - Number of sentences (default: 7)
- `-k <num>` - Number of keywords (default: 15)
- `--no-details` - Show only summary text
- `--encoding <enc>` - File encoding (default: utf-8)

**Examples:**
```bash
python document_cli.py summarize README.md
python document_cli.py summarize document.txt -s 10 -k 20
python document_cli.py summarize README.md -o summary.json
```

---

### 4. Batch Process Documents

Process multiple documents in a directory.

```bash
python document_cli.py batch <directory> [options]
```

**Options:**
- `-o <file>` - Save all summaries to file
- `-s <num>` - Sentences per summary (default: 5)
- `-k <num>` - Keywords per document (default: 10)
- `--show-summaries` - Display all summaries in console
- `--batch-size <N>` - Files per batch (default: 20)

**Examples:**
```bash
python document_cli.py batch ./docs/
python document_cli.py batch ./docs/ -o summaries.json
python document_cli.py batch ./docs/ --show-summaries
```

---

## Output Formats

### Text (.txt)
Plain text, readable format.

### JSON (.json)
Structured data with summary, keywords, metadata, and statistics.

**Example JSON output:**
```json
{
  "file_name": "document.md",
  "file_type": ".md",
  "success": true,
  "metadata": {
    "word_count": 500,
    "reading_time_minutes": 2.5,
    "heading_count": 5
  },
  "summary": "Document summary text...",
  "keywords": [
    {"word": "analysis", "frequency": 10}
  ]
}
```

---

## Quick Reference Card

### PDF Commands
```
COMMAND          PURPOSE                         EXAMPLE
--------         --------                        -------
info             Show PDF metadata               pdf_cli.py info file.pdf
parse            Extract text                    pdf_cli.py parse file.pdf -o out.txt
summarize        Generate summary                pdf_cli.py summarize file.pdf
batch            Process multiple PDFs           pdf_cli.py batch ./pdfs/ -o all.json
```

### Document Commands
```
COMMAND          PURPOSE                         EXAMPLE
--------         --------                        -------
info             Show document metadata          document_cli.py info README.md
analyze          Extract full metadata           document_cli.py analyze doc.txt -o out.json
summarize        Generate summary                document_cli.py summarize README.md
batch            Process multiple documents      document_cli.py batch ./docs/ -o all.json
```

### Common Options
```
OPTION           DESCRIPTION                     DEFAULT
------           -----------                     -------
-o FILE          Save output to file             (console output)
-s NUM           Number of summary sentences     7
-k NUM           Number of keywords              15
--show-text      Display extracted text          (disabled)
--show-keywords  Display top keywords            (disabled)
--max-size MB    Maximum file size               PDF: 25, Doc: 20
--encoding ENC   File encoding                   utf-8
--batch-size N   Files per batch                 PDF: 10, Doc: 20
--no-details     Show only summary               (disabled)
```

---

## Supported Document Types

| Type | Extensions | PDF CLI | Document CLI |
|------|-----------|---------|--------------|
| **PDF** | `.pdf` | ✅ | ❌ |
| **Text** | `.txt` | ❌ | ✅ |
| **Markdown** | `.md`, `.markdown` | ❌ | ✅ |
| **ReStructuredText** | `.rst` | ❌ | ✅ |
| **Log Files** | `.log` | ❌ | ✅ |
| **Word Documents** | `.docx` | ❌ | ✅ (requires python-docx) |

---

## Tips

**For paths with spaces, use quotes:**
```bash
python pdf_cli.py info "C:\My Documents\file.pdf"
python document_cli.py analyze "My Document.txt"
```

**Get help for any command:**
```bash
python pdf_cli.py --help
python pdf_cli.py summarize --help
python document_cli.py --help
python document_cli.py analyze --help
```

**Process mixed document types:**
```bash
# The batch command automatically finds all supported files
python document_cli.py batch ./my-docs/ -o all-summaries.json
```

**Combine PDF and document analysis:**
```bash
# Extract PDF text first
python pdf_cli.py parse document.pdf -o extracted.txt

# Then analyze as text
python document_cli.py analyze extracted.txt
```

**Export to JSON for programmatic use:**
```bash
python document_cli.py analyze document.md -o data.json
python pdf_cli.py summarize file.pdf -o data.json
```

---

## Common Use Cases

### 1. Quick Document Overview
```bash
python document_cli.py info README.md
```

### 2. Extract All Metadata
```bash
python document_cli.py analyze document.txt -o metadata.json
```

### 3. Generate Executive Summary
```bash
python document_cli.py summarize report.md -s 3 -o summary.txt
```

### 4. Batch Process Project Documentation
```bash
python document_cli.py batch ./docs/ -o project-summaries.json
```

### 5. Analyze PDF and Text Documents Together
```bash
# PDFs
python pdf_cli.py batch ./pdfs/ -o pdf-summaries.json

# Documents
python document_cli.py batch ./docs/ -o doc-summaries.json
```

---

## Troubleshooting

**Error: "File not found"**
- Check file path and use quotes for paths with spaces

**Error: "Unsupported file type"**
- Verify file extension is supported (see table above)
- For .docx files, ensure python-docx is installed

**Error: "File too large"**
- Increase limit with `--max-size` option
- Default: 25 MB for PDF, 20 MB for documents

**Error: "Encoding issues"**
- Try specifying encoding: `--encoding utf-8`
- Document analyzer auto-falls back to alternative encodings

**Performance issues with large batches**
- Reduce batch size: `--batch-size 5`
- Process smaller directories at a time
