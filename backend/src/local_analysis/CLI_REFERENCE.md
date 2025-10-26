# PDF Analysis CLI - Quick Reference

## Setup

Navigate to the CLI directory:
```bash
cd backend/src/local-analysis
```

---

## Commands

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

### 2. Extract Text

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

### 4. Batch Process

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

## Output Formats

### Text (.txt)
Plain text, readable format.

### JSON (.json)
Structured data with summary, keywords, and statistics.

---

## Quick Reference Card

```
COMMAND          PURPOSE                         EXAMPLE
--------         --------                        -------
info             Show PDF metadata               pdf_cli.py info file.pdf
parse            Extract text                    pdf_cli.py parse file.pdf -o out.txt
summarize        Generate summary                pdf_cli.py summarize file.pdf
batch            Process multiple PDFs           pdf_cli.py batch ./pdfs/ -o all.json

COMMON OPTIONS
-o FILE          Save output to file
-s NUM           Number of summary sentences
-k NUM           Number of keywords
--show-text      Display extracted text
--max-size MB    Maximum file size (default: 25)
--max-pages N    Maximum pages to process (default: 200)
--batch-size N   Files per batch (default: 10)
```

---

## Tips

**For paths with spaces, use quotes:**
```bash
python pdf_cli.py info "C:\My Documents\file.pdf"
```

**Get help for any command:**
```bash
python pdf_cli.py --help
python pdf_cli.py summarize --help
```

