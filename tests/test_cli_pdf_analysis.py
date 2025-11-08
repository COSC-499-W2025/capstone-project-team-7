import pytest
from pathlib import Path
from typing import List, Optional
from contextlib import contextmanager

from src.cli.app import CLIApp, ConsoleIO
from src.local_analysis.pdf_summarizer import create_summarizer, DocumentSummary
from src.local_analysis.pdf_parser import create_parser, PDFParseResult
from src.scanner.models import FileMetadata, ParseResult
from datetime import datetime, timezone


class StubIO(ConsoleIO):
    """Test IO that captures messages and provides canned responses."""
    
    def __init__(
        self,
        menu_choices: Optional[List[int]] = None,
        prompt_inputs: Optional[List[str]] = None,
    ):
        super().__init__()
        self._console = None  # Disable rich output for tests
        self._no_console = True
        self._menu_choices = iter(menu_choices or [])
        self._prompt_inputs = iter(prompt_inputs or [])
        self.messages: List[str] = []
    
    def write(self, message: str = "") -> None:
        self.messages.append(str(message))
    
    def write_success(self, message: str) -> None:
        self.messages.append(f"SUCCESS: {message}")
    
    def write_warning(self, message: str) -> None:
        self.messages.append(f"WARNING: {message}")
    
    def write_error(self, message: str) -> None:
        self.messages.append(f"ERROR: {message}")
    
    def prompt(self, message: str) -> str:
        self.messages.append(message)
        try:
            return next(self._prompt_inputs)
        except StopIteration:
            return ""
    
    def choose(self, title: str, options: List[str]) -> Optional[int]:
        self.messages.append(title)
        try:
            return next(self._menu_choices)
        except StopIteration:
            return None
    
    @contextmanager
    def status(self, message: str):
        self.messages.append(f"STATUS: {message}")
        yield


@pytest.fixture
def stub_io():
    return StubIO()


@pytest.fixture
def cli_app(stub_io):
    """Create a minimal CLIApp for testing."""
    return CLIApp(io=stub_io)


@pytest.fixture
def sample_pdf_text():
    """Sample PDF text content for testing."""
    return """
    This is a sample PDF document for testing the PDF analysis integration.
    The document contains multiple sentences with meaningful content.
    PDF analysis should extract key points and generate a summary.
    The summarizer uses extractive techniques to identify important sentences.
    This helps users understand document content quickly without reading everything.
    Testing the integration ensures the CLI workflow handles PDFs correctly.
    """


def test_pdf_summarizer_basic(sample_pdf_text):
    """Test that PDF summarizer generates a valid summary."""
    summarizer = create_summarizer(max_summary_sentences=3)
    summary = summarizer.generate_summary(sample_pdf_text, file_name="test.pdf")
    
    assert summary.success
    assert summary.file_name == "test.pdf"
    assert len(summary.summary_text) > 0
    assert len(summary.key_points) > 0
    assert len(summary.keywords) > 0
    assert isinstance(summary.statistics, dict)
    assert len(summary.statistics) > 0


def test_pdf_summarizer_empty_text():
    """Test that summarizer handles empty text gracefully."""
    summarizer = create_summarizer()
    summary = summarizer.generate_summary("", file_name="empty.pdf")
    
    assert not summary.success
    assert summary.error_message == "Empty text provided"


def test_cli_pdf_summaries_rendering(cli_app, stub_io, sample_pdf_text):
    """Test that CLI can render PDF summaries."""
    # Generate a sample summary
    summarizer = create_summarizer()
    summary = summarizer.generate_summary(sample_pdf_text, file_name="sample.pdf")
    
    # Add summary to CLI app
    cli_app._pdf_summaries = [summary]
    
    # Call the render method
    cli_app._render_pdf_summaries()
    
    # Verify output contains expected elements
    output = "\n".join(stub_io.messages)
    assert "sample.pdf" in output
    assert "SUMMARY" in output or "Summary" in output.lower()
    assert "STATISTICS" in output or "Statistics" in output.lower()
    assert "KEYWORDS" in output or "Keywords" in output.lower()


def test_cli_export_with_pdf_data(cli_app, sample_pdf_text):
    """Test that export includes PDF analysis data."""
    # Create a mock scan result
    now = datetime.now(timezone.utc)
    files = [
        FileMetadata(
            path="test.pdf",
            size_bytes=1024,
            mime_type="application/pdf",
            created_at=now,
            modified_at=now
        )
    ]
    parse_result = ParseResult(
        files=files,
        issues=[],
        summary={"files_processed": 1, "bytes_processed": 1024}
    )
    
    # Add PDF summary
    summarizer = create_summarizer()
    summary = summarizer.generate_summary(sample_pdf_text, file_name="test.pdf")
    cli_app._pdf_summaries = [summary]
    
    # Build export payload
    payload = cli_app._build_export_payload(
        parse_result,
        languages=[],
        archive=Path("test.zip")
    )
    
    # Verify PDF data is included
    assert "pdf_analysis" in payload
    assert payload["pdf_analysis"]["total_pdfs"] == 1
    assert payload["pdf_analysis"]["successful"] == 1
    assert len(payload["pdf_analysis"]["summaries"]) == 1
    
    pdf_data = payload["pdf_analysis"]["summaries"][0]
    assert pdf_data["file_name"] == "test.pdf"
    assert pdf_data["success"] is True
    assert pdf_data["summary"] is not None
    assert len(pdf_data["keywords"]) > 0


def test_cli_pdf_integration_workflow(cli_app, stub_io):
    """Test complete PDF workflow integration in CLI."""
    # Verify CLI app has PDF analysis capability
    assert hasattr(cli_app, '_pdf_summaries')
    assert hasattr(cli_app, '_pdf_results')
    assert hasattr(cli_app, '_render_pdf_summaries')
    
    # Verify initial state
    assert cli_app._pdf_summaries == []
    assert cli_app._pdf_results == []
    
    # Simulate adding PDF results
    sample_summary = DocumentSummary(
        file_name="test.pdf",
        summary_text="This is a test summary.",
        key_points=["Point 1", "Point 2"],
        keywords=[("test", 5), ("pdf", 3)],
        statistics={"total_words": 100},
        success=True
    )
    
    cli_app._pdf_summaries.append(sample_summary)
    
    # Verify rendering works
    cli_app._render_pdf_summaries()
    
    output = "\n".join(stub_io.messages)
    assert "test.pdf" in output
    assert "test summary" in output.lower()
