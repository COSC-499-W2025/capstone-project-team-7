"""
Local Analysis Module
In-house PDF parsing and summarization without external LLM dependencies
"""

try:
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
except ModuleNotFoundError as exc:
    # Allow non-PDF functionality/tests to run in environments where optional PDF deps
    # are not installed (for example, no network access for pip install).
    if exc.name != "pypdf":
        raise

    PDFParser = None
    PDFConfig = None
    PDFMetadata = None
    PDFParseResult = None
    PDFSummarizer = None
    SummaryConfig = None
    DocumentSummary = None

    def _missing_pdf_dependency(*_args, **_kwargs):
        raise ModuleNotFoundError("pypdf is required for PDF parsing features")

    create_parser = _missing_pdf_dependency
    create_summarizer = _missing_pdf_dependency

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
