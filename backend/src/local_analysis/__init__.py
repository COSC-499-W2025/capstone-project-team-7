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

from .git_repo import analyze_git_repo

from .contribution_analyzer import (
    ContributionAnalyzer,
    ProjectContributionMetrics,
    ContributorMetrics,
    ActivityBreakdown,
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
    
    # Git analysis
    'analyze_git_repo',
    
    # Contribution analysis
    'ContributionAnalyzer',
    'ProjectContributionMetrics',
    'ContributorMetrics',
    'ActivityBreakdown',
]

__version__ = '1.0.0'
