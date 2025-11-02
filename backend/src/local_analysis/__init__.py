"""
Local Analysis Module
In-house PDF parsing and summarization without external LLM dependencies
"""

from .pdf_parser import (
    PDFParser,
    PDFConfig,
    PDFMetadata,
    PDFParseResult,
    create_parser
)

from .pdf_summarizer import (
    PDFSummarizer,
    SummaryConfig,
    DocumentSummary,
    create_summarizer
)

from .media_analyzer import (
    MediaAnalyzer,
    MediaAnalyzerConfig,
)

__all__ = [
    # Parser
    'PDFParser',
    'PDFConfig',
    'PDFMetadata',
    'PDFParseResult',
    'create_parser',
    
    # Summarizer
    'PDFSummarizer',
    'SummaryConfig',
    'DocumentSummary',
    'create_summarizer',

    # Media analyzer
    'MediaAnalyzer',
    'MediaAnalyzerConfig',
]

__version__ = '1.0.0'
