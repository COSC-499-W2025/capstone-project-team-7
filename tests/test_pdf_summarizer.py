import pytest
from pathlib import Path
from src.local_analysis.pdf_summarizer import create_summarizer

@pytest.fixture
def sample_text():
    """Sample text with sentences long enough to pass the summarizer's filters.
    
    The summarizer requires sentences to have between 10-50 words.
    """
    return """
    This is a comprehensive test PDF document that contains enough words to be processed by the summarizer.
    The document has been carefully crafted to include several sentences with sufficient length for analysis.
    The summarizer should be able to extract key points and identify important keywords from this text.
    Each sentence in this document meets the minimum word count requirement for proper analysis and summarization.
    """

def test_generate_summary(sample_text):
    """Test that PDF summarizer generates a valid summary with proper text."""
    summarizer = create_summarizer(max_summary_sentences=3)
    summary = summarizer.generate_summary(sample_text, file_name="test.pdf")
    
    assert summary.success
    assert isinstance(summary.summary_text, str)
    assert len(summary.summary_text) > 0
    assert len(summary.key_points) > 0
    assert len(summary.keywords) > 0
    assert isinstance(summary.statistics, dict)
    assert summary.statistics.get("total_words", 0) > 0

# Edge case: empty text

def test_empty_pdf_summary():
    """Test that summarizer properly handles empty text with error."""
    summarizer = create_summarizer()
    summary = summarizer.generate_summary("", file_name="empty.pdf")
    
    # Empty text should fail gracefully
    assert not summary.success
    assert summary.error_message == "Empty text provided"
    assert summary.summary_text == ""
    assert summary.key_points == []
    assert summary.keywords == []
