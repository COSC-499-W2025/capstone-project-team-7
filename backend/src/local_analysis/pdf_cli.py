"""
PDF Analysis CLI Tool
Command-line interface for parsing and summarizing PDF documents
"""
import sys
import io
import argparse
from pathlib import Path
from typing import Optional, List
import json

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Import PDF analysis modules
from pdf_parser import create_parser, PDFConfig
from pdf_summarizer import create_summarizer, SummaryConfig


def print_header(text: str, char: str = "="):
    """Print a formatted header"""
    print(f"\n{char * 80}")
    print(f"  {text}")
    print(f"{char * 80}\n")


def print_section(text: str):
    """Print a formatted section"""
    print(f"\n{'-' * 80}")
    print(f"  {text}")
    print(f"{'-' * 80}\n")


def cmd_parse(args):
    """
    Parse PDF file(s) and extract text
    """
    print_header("PDF Parser - Text Extraction")
    
    # Create parser with configuration
    parser = create_parser(
        max_file_size_mb=args.max_size,
        max_pages_per_pdf=args.max_pages
    )
    
    print(f"Configuration:")
    print(f"  Max file size: {args.max_size} MB")
    print(f"  Max pages: {args.max_pages}")
    
    # Get PDF file(s)
    if args.file.is_file():
        pdf_files = [args.file]
    elif args.file.is_dir():
        pdf_files = list(args.file.glob("*.pdf"))
        if not pdf_files:
            print(f"\n✗ No PDF files found in directory: {args.file}")
            return 1
    else:
        print(f"\n✗ File or directory not found: {args.file}")
        return 1
    
    print(f"\nFound {len(pdf_files)} PDF file(s) to process")
    
    # Parse files
    results = []
    for pdf_file in pdf_files:
        print_section(f"Parsing: {pdf_file.name}")
        
        result = parser.extract_text_from_pdf(pdf_file)
        results.append(result)
        
        if result.success:
            print(f"✓ Success")
            print(f"  Pages: {result.num_pages}")
            print(f"  Size: {result.file_size_mb:.2f} MB")
            print(f"  Characters: {len(result.text_content):,}")
            print(f"  Words: {len(result.text_content.split()):,}")
            
            if result.metadata and result.metadata.title:
                print(f"  Title: {result.metadata.title}")
            
            if args.show_text:
                print(f"\n  Text Preview (first 500 chars):")
                print(f"  {result.text_content[:500]}...")
        else:
            print(f"✗ Failed: {result.error_message}")
    
    # Save to file if requested
    if args.output:
        print_section("Saving Results")
        
        output_data = []
        for result in results:
            if result.success:
                output_data.append({
                    'file_name': result.file_name,
                    'num_pages': result.num_pages,
                    'file_size_mb': result.file_size_mb,
                    'text': result.text_content,
                    'metadata': {
                        'title': result.metadata.title if result.metadata else None,
                        'author': result.metadata.author if result.metadata else None,
                    }
                })
        
        output_file = Path(args.output)
        
        if output_file.suffix == '.json':
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            print(f"✓ Saved JSON to: {output_file}")
        else:
            with open(output_file, 'w', encoding='utf-8') as f:
                for data in output_data:
                    f.write(f"File: {data['file_name']}\n")
                    f.write(f"Pages: {data['num_pages']}\n")
                    f.write(f"{'=' * 80}\n")
                    f.write(data['text'])
                    f.write(f"\n\n{'=' * 80}\n\n")
            print(f"✓ Saved text to: {output_file}")
    
    # Summary
    successful = sum(1 for r in results if r.success)
    print_section("Summary")
    print(f"Total files: {len(results)}")
    print(f"Successful: {successful}")
    print(f"Failed: {len(results) - successful}")
    
    return 0 if successful > 0 else 1


def cmd_summarize(args):
    """
    Parse PDF and generate summary
    """
    print_header("PDF Summarizer - Generate Summary")
    
    # Create parser and summarizer
    parser = create_parser(
        max_file_size_mb=args.max_size,
        max_pages_per_pdf=args.max_pages
    )
    
    summarizer = create_summarizer(
        max_summary_sentences=args.sentences,
        keyword_count=args.keywords
    )
    
    print(f"Configuration:")
    print(f"  Max file size: {args.max_size} MB")
    print(f"  Max pages: {args.max_pages}")
    print(f"  Summary sentences: {args.sentences}")
    print(f"  Keywords: {args.keywords}")
    
    # Get PDF file
    if not args.file.exists():
        print(f"\n✗ File not found: {args.file}")
        return 1
    
    # Parse PDF
    print_section(f"Parsing: {args.file.name}")
    
    result = parser.extract_text_from_pdf(args.file)
    
    if not result.success:
        print(f"✗ Failed to parse PDF: {result.error_message}")
        return 1
    
    print(f"✓ Parsed successfully")
    print(f"  Pages: {result.num_pages}")
    print(f"  Words: {len(result.text_content.split()):,}")
    
    # Generate summary
    print_section("Generating Summary")
    
    summary = summarizer.generate_summary(result.text_content, result.file_name)
    
    if not summary.success:
        print(f"✗ Failed to generate summary: {summary.error_message}")
        return 1
    
    print(f"✓ Summary generated successfully\n")
    
    # Display summary
    print_header("SUMMARY", "=")
    print(summary.summary_text)
    
    if not args.no_details:
        # Display key points
        print_header("KEY POINTS", "-")
        for i, point in enumerate(summary.key_points, 1):
            print(f"{i}. {point}\n")
        
        # Display keywords
        print_header("TOP KEYWORDS", "-")
        for keyword, freq in summary.keywords:
            print(f"  • {keyword:20s} ({freq} times)")
        
        # Display statistics
        print_header("STATISTICS", "-")
        print(f"  Total words:       {summary.statistics['total_words']:,}")
        print(f"  Total sentences:   {summary.statistics['total_sentences']:,}")
        print(f"  Unique words:      {summary.statistics['unique_words']:,}")
        print(f"  Avg sentence:      {summary.statistics['avg_sentence_length']:.1f} words")
        
        reading_time = summary.statistics['total_words'] / 200
        print(f"  Reading time:      {reading_time:.1f} minutes")
    
    # Save to file if requested
    if args.output:
        print_section("Saving Summary")
        
        output_file = Path(args.output)
        
        if output_file.suffix == '.json':
            output_data = {
                'file_name': summary.file_name,
                'summary': summary.summary_text,
                'key_points': summary.key_points,
                'keywords': [{'word': k, 'frequency': f} for k, f in summary.keywords],
                'statistics': summary.statistics
            }
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            print(f"✓ Saved JSON to: {output_file}")
        else:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"File: {summary.file_name}\n")
                f.write(f"{'=' * 80}\n\n")
                f.write(f"SUMMARY\n{'-' * 80}\n")
                f.write(f"{summary.summary_text}\n\n")
                f.write(f"KEY POINTS\n{'-' * 80}\n")
                for i, point in enumerate(summary.key_points, 1):
                    f.write(f"{i}. {point}\n")
                f.write(f"\nKEYWORDS\n{'-' * 80}\n")
                for keyword, freq in summary.keywords:
                    f.write(f"  • {keyword} ({freq} times)\n")
            print(f"✓ Saved summary to: {output_file}")
    
    print()
    return 0


def cmd_batch(args):
    """
    Process multiple PDFs and generate summaries for all
    """
    print_header("PDF Batch Processing - Parse & Summarize")
    
    # Create parser and summarizer
    parser = create_parser(
        max_file_size_mb=args.max_size,
        max_batch_size=args.batch_size,
        max_pages_per_pdf=args.max_pages
    )
    
    summarizer = create_summarizer(
        max_summary_sentences=args.sentences,
        keyword_count=args.keywords
    )
    
    # Get PDF files
    if args.directory.is_dir():
        pdf_files = list(args.directory.glob("*.pdf"))
        if not pdf_files:
            print(f"\n✗ No PDF files found in directory: {args.directory}")
            return 1
    else:
        print(f"\n✗ Directory not found: {args.directory}")
        return 1
    
    print(f"Found {len(pdf_files)} PDF file(s)")
    print(f"Batch size limit: {args.batch_size} files")
    
    # Process in batches
    all_results = []
    all_summaries = []
    
    for i in range(0, len(pdf_files), args.batch_size):
        batch = pdf_files[i:i + args.batch_size]
        batch_num = (i // args.batch_size) + 1
        
        print_section(f"Batch {batch_num} - Processing {len(batch)} files")
        
        # Parse batch
        results = parser.parse_batch(batch)
        all_results.extend(results)
        
        # Summarize successful parses
        for result in results:
            if result.success:
                print(f"  ✓ {result.file_name}: {result.num_pages} pages")
                
                summary = summarizer.generate_summary(result.text_content, result.file_name)
                all_summaries.append(summary)
            else:
                print(f"  ✗ {result.file_name}: {result.error_message}")
    
    # Display results
    print_section("Results Summary")
    
    successful = sum(1 for r in all_results if r.success)
    print(f"Total files: {len(all_results)}")
    print(f"Successful: {successful}")
    print(f"Failed: {len(all_results) - successful}")
    
    if args.show_summaries and all_summaries:
        for summary in all_summaries:
            print_header(f"Summary: {summary.file_name}", "-")
            print(summary.summary_text)
            print(f"\nTop keywords: {', '.join(k for k, _ in summary.keywords[:5])}")
    
    # Save to file if requested
    if args.output:
        print_section("Saving Results")
        
        output_file = Path(args.output)
        
        if output_file.suffix == '.json':
            output_data = []
            for summary in all_summaries:
                output_data.append({
                    'file_name': summary.file_name,
                    'summary': summary.summary_text,
                    'keywords': [{'word': k, 'frequency': f} for k, f in summary.keywords],
                    'statistics': summary.statistics
                })
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            print(f"✓ Saved JSON to: {output_file}")
        else:
            with open(output_file, 'w', encoding='utf-8') as f:
                for summary in all_summaries:
                    f.write(f"\n{'=' * 80}\n")
                    f.write(f"File: {summary.file_name}\n")
                    f.write(f"{'=' * 80}\n\n")
                    f.write(f"SUMMARY:\n{summary.summary_text}\n\n")
                    f.write(f"TOP KEYWORDS:\n")
                    for keyword, freq in summary.keywords[:10]:
                        f.write(f"  • {keyword} ({freq} times)\n")
                    f.write(f"\n")
            print(f"✓ Saved summaries to: {output_file}")
    
    print()
    return 0 if successful > 0 else 1


def cmd_info(args):
    """
    Show information about a PDF without parsing full content
    """
    print_header("PDF Information")
    
    if not args.file.exists():
        print(f"\n✗ File not found: {args.file}")
        return 1
    
    # Get file info
    file_size_mb = args.file.stat().st_size / (1024 * 1024)
    
    print(f"File: {args.file.name}")
    print(f"Path: {args.file}")
    print(f"Size: {file_size_mb:.2f} MB")
    
    # Quick parse for metadata
    parser = create_parser()
    result = parser.extract_text_from_pdf(args.file)
    
    if result.success:
        print(f"Pages: {result.num_pages}")
        
        if result.metadata:
            print(f"\nMetadata:")
            if result.metadata.title:
                print(f"  Title: {result.metadata.title}")
            if result.metadata.author:
                print(f"  Author: {result.metadata.author}")
            if result.metadata.subject:
                print(f"  Subject: {result.metadata.subject}")
            if result.metadata.creator:
                print(f"  Creator: {result.metadata.creator}")
            if result.metadata.creation_date:
                print(f"  Created: {result.metadata.creation_date}")
        
        word_count = len(result.text_content.split())
        reading_time = word_count / 200
        
        print(f"\nContent:")
        print(f"  Characters: {len(result.text_content):,}")
        print(f"  Words: {word_count:,}")
        print(f"  Est. reading time: {reading_time:.1f} minutes")
    else:
        print(f"\n✗ Could not read PDF: {result.error_message}")
        return 1
    
    print()
    return 0


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="PDF Analysis CLI - Parse and summarize PDF documents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Parse a single PDF
  python pdf_cli.py parse document.pdf
  
  # Parse and save text to file
  python pdf_cli.py parse document.pdf -o output.txt
  
  # Summarize a PDF
  python pdf_cli.py summarize document.pdf
  
  # Summarize with custom settings
  python pdf_cli.py summarize document.pdf -s 10 -k 20
  
  # Process all PDFs in a directory
  python pdf_cli.py batch ./pdfs/ -o summaries.json
  
  # Get PDF information
  python pdf_cli.py info document.pdf
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    subparsers.required = True
    
    # Parse command
    parse_parser = subparsers.add_parser('parse', help='Parse PDF and extract text')
    parse_parser.add_argument('file', type=Path, help='PDF file or directory to parse')
    parse_parser.add_argument('-o', '--output', help='Output file (text or JSON)')
    parse_parser.add_argument('--max-size', type=float, default=25.0, help='Max file size in MB (default: 25)')
    parse_parser.add_argument('--max-pages', type=int, default=200, help='Max pages to parse (default: 200)')
    parse_parser.add_argument('--show-text', action='store_true', help='Show text preview')
    parse_parser.set_defaults(func=cmd_parse)
    
    # Summarize command
    sum_parser = subparsers.add_parser('summarize', help='Summarize PDF content')
    sum_parser.add_argument('file', type=Path, help='PDF file to summarize')
    sum_parser.add_argument('-o', '--output', help='Output file (text or JSON)')
    sum_parser.add_argument('-s', '--sentences', type=int, default=7, help='Number of summary sentences (default: 7)')
    sum_parser.add_argument('-k', '--keywords', type=int, default=15, help='Number of keywords (default: 15)')
    sum_parser.add_argument('--max-size', type=float, default=25.0, help='Max file size in MB (default: 25)')
    sum_parser.add_argument('--max-pages', type=int, default=200, help='Max pages to parse (default: 200)')
    sum_parser.add_argument('--no-details', action='store_true', help='Show only summary text')
    sum_parser.set_defaults(func=cmd_summarize)
    
    # Batch command
    batch_parser = subparsers.add_parser('batch', help='Process multiple PDFs')
    batch_parser.add_argument('directory', type=Path, help='Directory containing PDFs')
    batch_parser.add_argument('-o', '--output', help='Output file (text or JSON)')
    batch_parser.add_argument('-s', '--sentences', type=int, default=5, help='Number of summary sentences (default: 5)')
    batch_parser.add_argument('-k', '--keywords', type=int, default=10, help='Number of keywords (default: 10)')
    batch_parser.add_argument('--max-size', type=float, default=25.0, help='Max file size in MB (default: 25)')
    batch_parser.add_argument('--max-pages', type=int, default=200, help='Max pages to parse (default: 200)')
    batch_parser.add_argument('--batch-size', type=int, default=10, help='Files per batch (default: 10)')
    batch_parser.add_argument('--show-summaries', action='store_true', help='Display all summaries')
    batch_parser.set_defaults(func=cmd_batch)
    
    # Info command
    info_parser = subparsers.add_parser('info', help='Show PDF information')
    info_parser.add_argument('file', type=Path, help='PDF file')
    info_parser.set_defaults(func=cmd_info)
    
    # Parse arguments
    args = parser.parse_args()
    
    # Execute command
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user")
        return 130
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
