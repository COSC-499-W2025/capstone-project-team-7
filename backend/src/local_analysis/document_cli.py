"""
Document Analysis CLI Tool
Command-line interface for analyzing text-based documents (.md, .txt, .docx, etc.)
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

# Import document analysis modules
from document_analyzer import create_analyzer, DocumentConfig


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


def cmd_info(args):
    """
    Show information about a document without full analysis
    """
    print_header("Document Information")
    
    if not args.file.exists():
        print(f"\n✗ File not found: {args.file}")
        return 1
    
    # Get file info
    file_size_mb = args.file.stat().st_size / (1024 * 1024)
    file_type = args.file.suffix.lower()
    
    print(f"File: {args.file.name}")
    print(f"Path: {args.file}")
    print(f"Type: {file_type}")
    print(f"Size: {file_size_mb:.2f} MB")
    
    # Quick analysis
    analyzer = create_analyzer()
    result = analyzer.analyze_document(args.file)
    
    if result.success and result.metadata:
        print(f"\nContent:")
        print(f"  Characters: {result.metadata.character_count:,}")
        print(f"  Words: {result.metadata.word_count:,}")
        print(f"  Lines: {result.metadata.line_count:,}")
        print(f"  Paragraphs: {result.metadata.paragraph_count:,}")
        print(f"  Est. reading time: {result.metadata.reading_time_minutes:.1f} minutes")
        
        # Format-specific info
        if file_type in ['.md', '.markdown'] and result.metadata.heading_count > 0:
            print(f"\nMarkdown Features:")
            print(f"  Headings: {result.metadata.heading_count}")
            print(f"  Code blocks: {result.metadata.code_blocks}")
            print(f"  Links: {result.metadata.links}")
            print(f"  Images: {result.metadata.images}")
        
        if file_type == '.docx' and result.metadata.pages:
            print(f"\nDocument Structure:")
            print(f"  Pages: {result.metadata.pages}")
            if result.metadata.sections:
                print(f"  Sections: {result.metadata.sections}")
    else:
        print(f"\n✗ Could not analyze document: {result.error_message}")
        return 1
    
    print()
    return 0


def cmd_analyze(args):
    """
    Analyze document(s) and extract metadata
    """
    print_header("Document Analyzer - Extract Metadata")
    
    # Create analyzer with configuration
    analyzer = create_analyzer(
        max_file_size_mb=args.max_size,
        max_batch_size=args.batch_size,
        encoding=args.encoding
    )
    
    print(f"Configuration:")
    print(f"  Max file size: {args.max_size} MB")
    print(f"  Encoding: {args.encoding}")
    
    # Get document file(s)
    if args.file.is_file():
        doc_files = [args.file]
    elif args.file.is_dir():
        # Support multiple extensions
        extensions = ['.txt', '.md', '.markdown', '.rst', '.log', '.docx']
        doc_files = []
        for ext in extensions:
            doc_files.extend(args.file.glob(f"*{ext}"))
        
        if not doc_files:
            print(f"\n✗ No supported document files found in directory: {args.file}")
            return 1
    else:
        print(f"\n✗ File or directory not found: {args.file}")
        return 1
    
    print(f"\nFound {len(doc_files)} document file(s) to process")
    
    # Analyze files
    results = []
    for doc_file in doc_files:
        print_section(f"Analyzing: {doc_file.name}")
        
        result = analyzer.analyze_document(doc_file)
        results.append(result)
        
        if result.success and result.metadata:
            print(f"✓ Success")
            print(f"  Type: {result.file_type}")
            print(f"  Words: {result.metadata.word_count:,}")
            print(f"  Characters: {result.metadata.character_count:,}")
            print(f"  Reading time: {result.metadata.reading_time_minutes:.1f} min")
            
            if result.file_type in ['.md', '.markdown'] and result.metadata.heading_count > 0:
                print(f"  Headings: {result.metadata.heading_count}")
            
            if args.show_keywords and result.keywords:
                print(f"\n  Top keywords:")
                for keyword, freq in result.keywords[:5]:
                    print(f"    • {keyword} ({freq}x)")
        else:
            print(f"✗ Failed: {result.error_message}")
    
    # Save to file if requested
    if args.output:
        print_section("Saving Results")
        
        output_file = Path(args.output)
        
        if output_file.suffix == '.json':
            output_data = []
            for result in results:
                if result.success:
                    output_data.append(analyzer.to_json(result))
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            print(f"✓ Saved JSON to: {output_file}")
        else:
            with open(output_file, 'w', encoding='utf-8') as f:
                for result in results:
                    if result.success and result.metadata:
                        f.write(f"File: {result.file_name}\n")
                        f.write(f"Type: {result.file_type}\n")
                        f.write(f"Words: {result.metadata.word_count:,}\n")
                        f.write(f"Reading time: {result.metadata.reading_time_minutes:.1f} min\n")
                        f.write(f"{'=' * 80}\n\n")
            print(f"✓ Saved metadata to: {output_file}")
    
    # Summary
    successful = sum(1 for r in results if r.success)
    print_section("Summary")
    print(f"Total files: {len(results)}")
    print(f"Successful: {successful}")
    print(f"Failed: {len(results) - successful}")
    
    return 0 if successful > 0 else 1


def cmd_summarize(args):
    """
    Analyze document and generate summary
    """
    print_header("Document Summarizer - Generate Summary")
    
    # Create analyzer
    analyzer = create_analyzer(
        max_file_size_mb=args.max_size,
        encoding=args.encoding
    )
    
    print(f"Configuration:")
    print(f"  Max file size: {args.max_size} MB")
    print(f"  Summary sentences: {args.sentences}")
    print(f"  Keywords: {args.keywords}")
    
    # Get document file
    if not args.file.exists():
        print(f"\n✗ File not found: {args.file}")
        return 1
    
    # Analyze document
    print_section(f"Analyzing: {args.file.name}")
    
    result = analyzer.analyze_document(args.file)
    
    if not result.success:
        print(f"✗ Failed to analyze document: {result.error_message}")
        return 1
    
    if not result.metadata:
        print(f"✗ No metadata extracted from document")
        return 1
    
    print(f"✓ Analyzed successfully")
    print(f"  Type: {result.file_type}")
    print(f"  Words: {result.metadata.word_count:,}")
    print(f"  Reading time: {result.metadata.reading_time_minutes:.1f} min")
    
    # Display summary
    if result.summary:
        print_header("SUMMARY", "=")
        print(result.summary)
    
    if not args.no_details:
        # Display keywords
        if result.keywords:
            print_header("TOP KEYWORDS", "-")
            for keyword, freq in result.keywords[:args.keywords]:
                print(f"  • {keyword:20s} ({freq} times)")
        
        # Display key topics
        if result.key_topics:
            print_header("KEY TOPICS", "-")
            for i, topic in enumerate(result.key_topics, 1):
                print(f"  {i}. {topic}")
        
        # Display statistics
        if result.statistics:
            print_header("STATISTICS", "-")
            if 'total_words' in result.statistics:
                print(f"  Total words:       {result.statistics['total_words']:,}")
            if 'total_sentences' in result.statistics:
                print(f"  Total sentences:   {result.statistics['total_sentences']:,}")
            if 'unique_words' in result.statistics:
                print(f"  Unique words:      {result.statistics['unique_words']:,}")
        
        # Format-specific details
        if result.file_type in ['.md', '.markdown'] and result.metadata.headings:
            print_header("DOCUMENT STRUCTURE", "-")
            for heading in result.metadata.headings:
                print(f"  {heading}")
    
    # Save to file if requested
    if args.output:
        print_section("Saving Summary")
        
        output_file = Path(args.output)
        
        if output_file.suffix == '.json':
            output_data = analyzer.to_json(result)
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            print(f"✓ Saved JSON to: {output_file}")
        else:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"File: {result.file_name}\n")
                f.write(f"Type: {result.file_type}\n")
                f.write(f"{'=' * 80}\n\n")
                f.write(f"SUMMARY\n{'-' * 80}\n")
                if result.summary:
                    f.write(f"{result.summary}\n\n")
                if result.keywords:
                    f.write(f"KEYWORDS\n{'-' * 80}\n")
                    for keyword, freq in result.keywords[:args.keywords]:
                        f.write(f"  • {keyword} ({freq} times)\n")
            print(f"✓ Saved summary to: {output_file}")
    
    print()
    return 0


def cmd_batch(args):
    """
    Process multiple documents and generate summaries for all
    """
    print_header("Document Batch Processing - Analyze & Summarize")
    
    # Create analyzer
    analyzer = create_analyzer(
        max_file_size_mb=args.max_size,
        max_batch_size=args.batch_size,
        encoding=args.encoding
    )
    
    # Get document files
    if args.directory.is_dir():
        extensions = ['.txt', '.md', '.markdown', '.rst', '.log', '.docx']
        doc_files = []
        for ext in extensions:
            doc_files.extend(args.directory.glob(f"*{ext}"))
        
        if not doc_files:
            print(f"\n✗ No supported document files found in directory: {args.directory}")
            return 1
    else:
        print(f"\n✗ Directory not found: {args.directory}")
        return 1
    
    print(f"Found {len(doc_files)} document file(s)")
    print(f"Batch size limit: {args.batch_size} files")
    
    # Process in batches
    all_results = []
    
    for i in range(0, len(doc_files), args.batch_size):
        batch = doc_files[i:i + args.batch_size]
        batch_num = (i // args.batch_size) + 1
        
        print_section(f"Batch {batch_num} - Processing {len(batch)} files")
        
        # Analyze batch
        results = analyzer.analyze_batch(batch)
        all_results.extend(results)
        
        for result in results:
            if result.success and result.metadata:
                print(f"  ✓ {result.file_name}: {result.metadata.word_count} words")
            else:
                print(f"  ✗ {result.file_name}: {result.error_message}")
    
    # Display results
    print_section("Results Summary")
    
    successful = sum(1 for r in all_results if r.success)
    print(f"Total files: {len(all_results)}")
    print(f"Successful: {successful}")
    print(f"Failed: {len(all_results) - successful}")
    
    if args.show_summaries:
        for result in all_results:
            if result.success and result.summary:
                print_header(f"Summary: {result.file_name}", "-")
                print(result.summary)
                if result.keywords:
                    print(f"\nTop keywords: {', '.join(k for k, _ in result.keywords[:5])}")
    
    # Save to file if requested
    if args.output:
        print_section("Saving Results")
        
        output_file = Path(args.output)
        
        if output_file.suffix == '.json':
            output_data = []
            for result in all_results:
                if result.success:
                    output_data.append(analyzer.to_json(result))
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            print(f"✓ Saved JSON to: {output_file}")
        else:
            with open(output_file, 'w', encoding='utf-8') as f:
                for result in all_results:
                    if result.success and result.summary:
                        f.write(f"\n{'=' * 80}\n")
                        f.write(f"File: {result.file_name}\n")
                        f.write(f"{'=' * 80}\n\n")
                        f.write(f"SUMMARY:\n{result.summary}\n\n")
                        if result.keywords:
                            f.write(f"TOP KEYWORDS:\n")
                            for keyword, freq in result.keywords[:10]:
                                f.write(f"  • {keyword} ({freq} times)\n")
                        f.write(f"\n")
            print(f"✓ Saved summaries to: {output_file}")
    
    print()
    return 0 if successful > 0 else 1


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Document Analysis CLI - Analyze text-based documents (.txt, .md, .docx, etc.)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze a single document
  python document_cli.py analyze document.txt
  
  # Analyze and save metadata to file
  python document_cli.py analyze document.md -o output.json
  
  # Summarize a document
  python document_cli.py summarize README.md
  
  # Summarize with custom settings
  python document_cli.py summarize document.txt -s 10 -k 20
  
  # Process all documents in a directory
  python document_cli.py batch ./docs/ -o summaries.json
  
  # Get document information
  python document_cli.py info document.md
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    subparsers.required = True
    
    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze document and extract metadata')
    analyze_parser.add_argument('file', type=Path, help='Document file or directory to analyze')
    analyze_parser.add_argument('-o', '--output', help='Output file (text or JSON)')
    analyze_parser.add_argument('--max-size', type=float, default=20.0, help='Max file size in MB (default: 20)')
    analyze_parser.add_argument('--encoding', default='utf-8', help='File encoding (default: utf-8)')
    analyze_parser.add_argument('--batch-size', type=int, default=20, help='Max files per batch (default: 20)')
    analyze_parser.add_argument('--show-keywords', action='store_true', help='Show top keywords')
    analyze_parser.set_defaults(func=cmd_analyze)
    
    # Summarize command
    sum_parser = subparsers.add_parser('summarize', help='Summarize document content')
    sum_parser.add_argument('file', type=Path, help='Document file to summarize')
    sum_parser.add_argument('-o', '--output', help='Output file (text or JSON)')
    sum_parser.add_argument('-s', '--sentences', type=int, default=7, help='Number of summary sentences (default: 7)')
    sum_parser.add_argument('-k', '--keywords', type=int, default=15, help='Number of keywords (default: 15)')
    sum_parser.add_argument('--max-size', type=float, default=20.0, help='Max file size in MB (default: 20)')
    sum_parser.add_argument('--encoding', default='utf-8', help='File encoding (default: utf-8)')
    sum_parser.add_argument('--no-details', action='store_true', help='Show only summary text')
    sum_parser.set_defaults(func=cmd_summarize)
    
    # Batch command
    batch_parser = subparsers.add_parser('batch', help='Process multiple documents')
    batch_parser.add_argument('directory', type=Path, help='Directory containing documents')
    batch_parser.add_argument('-o', '--output', help='Output file (text or JSON)')
    batch_parser.add_argument('-s', '--sentences', type=int, default=5, help='Number of summary sentences (default: 5)')
    batch_parser.add_argument('-k', '--keywords', type=int, default=10, help='Number of keywords (default: 10)')
    batch_parser.add_argument('--max-size', type=float, default=20.0, help='Max file size in MB (default: 20)')
    batch_parser.add_argument('--encoding', default='utf-8', help='File encoding (default: utf-8)')
    batch_parser.add_argument('--batch-size', type=int, default=20, help='Files per batch (default: 20)')
    batch_parser.add_argument('--show-summaries', action='store_true', help='Display all summaries')
    batch_parser.set_defaults(func=cmd_batch)
    
    # Info command
    info_parser = subparsers.add_parser('info', help='Show document information')
    info_parser.add_argument('file', type=Path, help='Document file')
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
