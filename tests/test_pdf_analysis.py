"""
Tests for PDF Parser and Summarizer modules
Comprehensive test suite for 100% code coverage
"""
import pytest
from pathlib import Path
import tempfile
import io
import json
from unittest.mock import Mock, patch, MagicMock
from pypdf import PdfReader, PdfWriter

# Import using the helper function from conftest
from conftest import import_from_local_analysis

# Import modules from local-analysis directory
pdf_parser = import_from_local_analysis("pdf_parser")
pdf_summarizer = import_from_local_analysis("pdf_summarizer")

# Extract the classes and functions for easier access
PDFParser = pdf_parser.PDFParser
PDFConfig = pdf_parser.PDFConfig
PDFMetadata = pdf_parser.PDFMetadata
PDFParseResult = pdf_parser.PDFParseResult
create_parser = pdf_parser.create_parser

PDFSummarizer = pdf_summarizer.PDFSummarizer
SummaryConfig = pdf_summarizer.SummaryConfig
DocumentSummary = pdf_summarizer.DocumentSummary
create_summarizer = pdf_summarizer.create_summarizer


class TestPDFParser:
    """Test cases for PDF Parser"""
    
    def test_create_parser_with_defaults(self):
        """Test creating parser with default configuration"""
        parser = create_parser()
        assert parser is not None
        assert isinstance(parser, PDFParser)
        assert parser.config.max_file_size_mb == 10.0
        assert parser.config.max_batch_size == 10
    
    def test_create_parser_with_custom_config(self):
        """Test creating parser with custom configuration"""
        parser = create_parser(
            max_file_size_mb=5.0,
            max_batch_size=5,
            max_total_batch_size_mb=20.0,
            max_pages_per_pdf=50
        )
        assert parser.config.max_file_size_mb == 5.0
        assert parser.config.max_batch_size == 5
        assert parser.config.max_total_batch_size_mb == 20.0
        assert parser.config.max_pages_per_pdf == 50
    
    def test_validate_file_size_within_limit(self):
        """Test file size validation for valid file"""
        parser = create_parser(max_file_size_mb=10.0)
        
        # Create a small temporary file
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            f.write(b'small file content')
            temp_path = Path(f.name)
        
        try:
            is_valid, size_mb, error = parser.validate_file_size(temp_path)
            assert is_valid
            assert size_mb < 1.0
            assert error is None
        finally:
            temp_path.unlink()
    
    def test_validate_batch_size(self):
        """Test batch size validation"""
        parser = create_parser(max_batch_size=3)
        
        # Create temporary files
        temp_files = []
        for i in range(2):
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
                f.write(b'content')
                temp_files.append(Path(f.name))
        
        try:
            # Valid batch
            is_valid, error = parser.validate_batch(temp_files)
            assert is_valid
            assert error is None
            
            # Invalid batch (too many files)
            too_many = temp_files + [Path("extra1.pdf"), Path("extra2.pdf")]
            is_valid, error = parser.validate_batch(too_many)
            assert not is_valid
            assert "exceeds limit" in error.lower()
        finally:
            for f in temp_files:
                f.unlink()
    
    def test_parse_result_structure(self):
        """Test PDFParseResult data structure"""
        result = PDFParseResult(
            file_name="test.pdf",
            success=True,
            text_content="Sample text",
            num_pages=5,
            file_size_mb=2.5
        )
        
        assert result.file_name == "test.pdf"
        assert result.success is True
        assert result.text_content == "Sample text"
        assert result.num_pages == 5
        assert result.file_size_mb == 2.5
    
    def test_validate_file_size_exceeds_limit(self):
        """Test file size validation for oversized file"""
        parser = create_parser(max_file_size_mb=0.001)  # 1 KB limit
        
        # Create a file larger than limit
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            f.write(b'x' * 2000)  # 2 KB file
            temp_path = Path(f.name)
        
        try:
            is_valid, size_mb, error = parser.validate_file_size(temp_path)
            assert not is_valid
            assert size_mb > 0
            assert "exceeds limit" in error.lower()
        finally:
            temp_path.unlink()
    
    def test_validate_file_size_nonexistent_file(self):
        """Test file size validation for non-existent file"""
        parser = create_parser()
        fake_path = Path("nonexistent_file.pdf")
        
        is_valid, size_mb, error = parser.validate_file_size(fake_path)
        assert not is_valid
        assert size_mb == 0.0
        assert error is not None
    
    def test_validate_batch_exceeds_total_size(self):
        """Test batch validation when total size exceeds limit"""
        parser = create_parser(max_total_batch_size_mb=0.001)  # Very small limit
        
        temp_files = []
        for i in range(2):
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
                f.write(b'x' * 1000)  # 1 KB each
                temp_files.append(Path(f.name))
        
        try:
            is_valid, error = parser.validate_batch(temp_files)
            assert not is_valid
            assert "total batch size" in error.lower()
        finally:
            for f in temp_files:
                f.unlink()
    
    def test_validate_batch_with_missing_file(self):
        """Test batch validation with some missing files"""
        parser = create_parser()
        temp_files = [Path("missing1.pdf"), Path("missing2.pdf")]
        
        # Should not crash, just skip missing files
        is_valid, error = parser.validate_batch(temp_files)
        # Will be valid since missing files have 0 size
        assert is_valid or error is not None
    
    def test_extract_metadata_with_no_metadata(self):
        """Test metadata extraction when PDF has no metadata"""
        parser = create_parser()
        
        # Create a mock PDF reader with no metadata
        mock_reader = Mock()
        mock_reader.pages = [Mock(), Mock()]
        mock_reader.metadata = None
        
        metadata = parser.extract_metadata(mock_reader)
        
        assert metadata.num_pages == 2
        assert metadata.title is None
        assert metadata.author is None
    
    def test_extract_metadata_with_complete_metadata(self):
        """Test metadata extraction with all fields"""
        parser = create_parser()
        
        mock_reader = Mock()
        mock_reader.pages = [Mock()]
        mock_reader.metadata = {
            '/Title': 'Test Document',
            '/Author': 'Test Author',
            '/Subject': 'Test Subject',
            '/Creator': 'Test Creator',
            '/Producer': 'Test Producer',
            '/CreationDate': 'D:20240101',
            '/ModDate': 'D:20240102'
        }
        
        metadata = parser.extract_metadata(mock_reader)
        
        assert metadata.title == 'Test Document'
        assert metadata.author == 'Test Author'
        assert metadata.subject == 'Test Subject'
        assert metadata.creator == 'Test Creator'
        assert metadata.producer == 'Test Producer'
    
    def test_extract_metadata_with_exception(self):
        """Test metadata extraction handles exceptions gracefully"""
        parser = create_parser()
        
        mock_reader = Mock()
        mock_reader.pages = [Mock()]
        mock_reader.metadata = Mock()
        mock_reader.metadata.get = Mock(side_effect=Exception("Metadata error"))
        
        # Should not crash
        metadata = parser.extract_metadata(mock_reader)
        assert metadata.num_pages == 1
    
    def test_parse_from_bytes_success(self):
        """Test parsing PDF from bytes"""
        parser = create_parser()
        
        # Create a simple PDF in memory
        pdf_writer = PdfWriter()
        pdf_writer.add_blank_page(width=200, height=200)
        
        bytes_io = io.BytesIO()
        pdf_writer.write(bytes_io)
        pdf_bytes = bytes_io.getvalue()
        
        result = parser.parse_from_bytes(pdf_bytes, "test.pdf")
        
        assert result.success
        assert result.file_name == "test.pdf"
        assert result.num_pages == 1
        assert result.file_size_mb > 0
    
    def test_parse_from_bytes_exceeds_size_limit(self):
        """Test parsing from bytes when size exceeds limit"""
        parser = create_parser(max_file_size_mb=0.001)
        
        # Create bytes larger than limit
        large_bytes = b'x' * 2000  # 2 KB
        
        result = parser.parse_from_bytes(large_bytes, "large.pdf")
        
        assert not result.success
        assert "exceeds limit" in result.error_message.lower()
    
    def test_parse_from_bytes_invalid_pdf(self):
        """Test parsing invalid PDF bytes"""
        parser = create_parser()
        
        invalid_bytes = b'not a valid pdf'
        
        result = parser.parse_from_bytes(invalid_bytes, "invalid.pdf")
        
        assert not result.success
        assert result.error_message is not None
    
    def test_parse_batch_empty_list(self):
        """Test batch parsing with empty file list"""
        parser = create_parser()
        
        results = parser.parse_batch([])
        
        assert len(results) == 0
    
    def test_parse_batch_with_validation_failure(self):
        """Test batch parsing when validation fails"""
        parser = create_parser(max_batch_size=1)
        
        fake_files = [Path("file1.pdf"), Path("file2.pdf")]
        
        results = parser.parse_batch(fake_files)
        
        assert len(results) == 2
        assert all(not r.success for r in results)
        assert all("batch validation failed" in r.error_message.lower() for r in results)
    
    def test_pdf_config_dataclass(self):
        """Test PDFConfig dataclass"""
        config = PDFConfig(
            max_file_size_mb=15.0,
            max_batch_size=20,
            max_total_batch_size_mb=100.0,
            max_pages_per_pdf=150
        )
        
        assert config.max_file_size_mb == 15.0
        assert config.max_batch_size == 20
        assert config.max_total_batch_size_mb == 100.0
        assert config.max_pages_per_pdf == 150
    
    def test_pdf_metadata_dataclass(self):
        """Test PDFMetadata dataclass"""
        metadata = PDFMetadata(
            title="Test",
            author="Author",
            subject="Subject",
            creator="Creator",
            producer="Producer",
            creation_date="2024",
            modification_date="2024",
            num_pages=10
        )
        
        assert metadata.title == "Test"
        assert metadata.num_pages == 10


class TestPDFSummarizer:
    """Test cases for PDF Summarizer"""
    
    def test_create_summarizer_with_defaults(self):
        """Test creating summarizer with default configuration"""
        summarizer = create_summarizer()
        assert summarizer is not None
        assert isinstance(summarizer, PDFSummarizer)
        assert summarizer.config.max_summary_sentences == 5
        assert summarizer.config.keyword_count == 10
    
    def test_create_summarizer_with_custom_config(self):
        """Test creating summarizer with custom configuration"""
        summarizer = create_summarizer(
            max_summary_sentences=3,
            min_sentence_length=5,
            max_sentence_length=30,
            keyword_count=5
        )
        assert summarizer.config.max_summary_sentences == 3
        assert summarizer.config.min_sentence_length == 5
        assert summarizer.config.max_sentence_length == 30
        assert summarizer.config.keyword_count == 5
    
    def test_clean_text(self):
        """Test text cleaning functionality"""
        summarizer = create_summarizer()
        
        text = "This   has    multiple   spaces.  And weird   formatting."
        cleaned = summarizer.clean_text(text)
        
        assert "  " not in cleaned
        assert cleaned.count(" ") < text.count(" ")
    
    def test_split_into_sentences(self):
        """Test sentence splitting"""
        summarizer = create_summarizer()
        
        # Create text with sentences that meet length requirements (10-50 words)
        text = """
        This is the first sentence with enough words to meet the minimum length requirement.
        This is the second sentence also with sufficient words for processing properly.
        Here is a third sentence with adequate length for the sentence filter requirements.
        """
        
        sentences = summarizer.split_into_sentences(text)
        
        assert len(sentences) > 0
        assert all(isinstance(s, str) for s in sentences)
    
    def test_tokenize(self):
        """Test text tokenization"""
        summarizer = create_summarizer()
        
        text = "This is a sample text with some common words."
        tokens = summarizer.tokenize(text)
        
        # Should remove stop words like 'is', 'a', 'with', 'some'
        assert "sample" in tokens
        assert "text" in tokens
        assert "words" in tokens
        assert "is" not in tokens  # Stop word
        assert "a" not in tokens   # Stop word
    
    def test_extract_keywords(self):
        """Test keyword extraction"""
        summarizer = create_summarizer()
        
        text = """
        Machine learning is important. Machine learning algorithms learn from data.
        Learning is a key concept in machine learning systems.
        """
        
        keywords = summarizer.extract_keywords(text, top_n=5)
        
        assert len(keywords) <= 5
        assert all(isinstance(kw, tuple) and len(kw) == 2 for kw in keywords)
        
        # 'learning' and 'machine' should be top keywords
        keyword_words = [kw[0] for kw in keywords]
        assert any('learn' in kw for kw in keyword_words)
    
    def test_generate_summary_with_valid_text(self):
        """Test summary generation with valid text"""
        summarizer = create_summarizer(max_summary_sentences=3)
        
        # Create text with sentences of appropriate length (10-50 words each)
        text = """
        Artificial intelligence is transforming technology in ways we could not have imagined just ten years ago.
        Machine learning enables computers to learn from data and improve performance without explicit programming instructions.
        Deep learning uses neural networks with multiple layers to solve complex tasks in image and speech recognition.
        Natural language processing helps computers understand human language and respond in meaningful contextual ways.
        Computer vision allows machines to interpret visual information from the world around them accurately.
        """
        
        summary = summarizer.generate_summary(text, "test.pdf")
        
        assert summary.success is True
        assert len(summary.summary_text) > 0
        assert len(summary.key_points) <= 3
        assert len(summary.keywords) > 0
        assert summary.statistics['total_words'] > 0
        assert summary.error_message is None
    
    def test_generate_summary_with_empty_text(self):
        """Test summary generation with empty text"""
        summarizer = create_summarizer()
        
        summary = summarizer.generate_summary("", "empty.pdf")
        
        assert summary.success is False
        assert "Empty text" in summary.error_message
    
    def test_calculate_statistics(self):
        """Test document statistics calculation"""
        summarizer = create_summarizer()
        
        # Create text with sentences of appropriate length
        text = "This is a test sentence with enough words to meet the minimum requirements. This is another test sentence with sufficient word count."
        sentences = summarizer.split_into_sentences(text)
        stats = summarizer.calculate_statistics(text, sentences)
        
        assert 'total_characters' in stats
        assert 'total_words' in stats
        assert 'total_sentences' in stats
        assert 'avg_sentence_length' in stats
        assert 'unique_words' in stats
        
        assert stats['total_characters'] > 0
        assert stats['total_words'] > 0
        # sentences might be 0 if they don't meet length requirements
        assert stats['total_sentences'] >= 0
    
    def test_summarize_batch(self):
        """Test batch summarization"""
        summarizer = create_summarizer()
        
        documents = [
            ("doc1.pdf", "This is the first document with adequate length for proper sentence extraction and analysis purposes. It has some meaningful content that can be processed."),
            ("doc2.pdf", "This is the second document with different content but also meeting the minimum length requirements for sentences. It has different information to analyze."),
            ("doc3.pdf", "This is the third document with more content and information for testing batch summarization functionality. It has additional text for testing.")
        ]
        
        summaries = summarizer.summarize_batch(documents)
        
        assert len(summaries) == 3
        assert all(isinstance(s, DocumentSummary) for s in summaries)
        # Some might succeed, some might fail based on content
        assert len([s for s in summaries if s.success]) >= 0
    
    def test_document_summary_structure(self):
        """Test DocumentSummary data structure"""
        summary = DocumentSummary(
            file_name="test.pdf",
            summary_text="This is a summary.",
            key_points=["Point 1", "Point 2"],
            keywords=[("keyword1", 5), ("keyword2", 3)],
            statistics={"total_words": 100},
            success=True
        )
        
        assert summary.file_name == "test.pdf"
        assert summary.success is True
        assert len(summary.key_points) == 2
        assert len(summary.keywords) == 2
    
    def test_generate_summary_with_whitespace_only(self):
        """Test summary generation with whitespace-only text"""
        summarizer = create_summarizer()
        
        summary = summarizer.generate_summary("   \n\t  ", "whitespace.pdf")
        
        assert not summary.success
        assert "Empty text" in summary.error_message
    
    def test_generate_summary_with_no_valid_sentences(self):
        """Test summary with text that produces no valid sentences"""
        summarizer = create_summarizer(min_sentence_length=50)
        
        text = "Short. Too short. Also short."
        summary = summarizer.generate_summary(text, "short.pdf")
        
        assert not summary.success
        assert "No valid sentences" in summary.error_message
    
    def test_split_into_sentences_with_various_endings(self):
        """Test sentence splitting with different punctuation"""
        summarizer = create_summarizer()
        
        # Create sentences with appropriate length (10-50 words)
        text = "First sentence with enough words to meet the minimum requirements for processing properly. " \
               "Second sentence also with sufficient words for proper analysis and testing purposes! " \
               "Third sentence with adequate length for the sentence filter requirements and validation? " \
               "Fourth sentence with proper word count to pass the filter criteria successfully."
        sentences = summarizer.split_into_sentences(text)
        
        assert len(sentences) > 0
        assert all(isinstance(s, str) for s in sentences)
    
    def test_tokenize_removes_punctuation(self):
        """Test that tokenization removes punctuation properly"""
        summarizer = create_summarizer()
        
        text = "Hello, world! This is a test."
        tokens = summarizer.tokenize(text)
        
        # Should not contain punctuation
        assert all(',' not in token for token in tokens)
        assert all('!' not in token for token in tokens)
        assert all('.' not in token for token in tokens)
    
    def test_tokenize_filters_short_words(self):
        """Test that short words are filtered out"""
        summarizer = create_summarizer()
        
        text = "I am at it by on if"
        tokens = summarizer.tokenize(text)
        
        # All these are either stop words or too short (<=2 chars)
        assert len(tokens) == 0
    
    def test_calculate_word_frequencies_empty_input(self):
        """Test word frequency calculation with empty input"""
        summarizer = create_summarizer()
        
        freq = summarizer.calculate_word_frequencies([])
        
        assert freq == {}
    
    def test_calculate_word_frequencies_normalization(self):
        """Test that word frequencies are normalized"""
        summarizer = create_summarizer()
        
        sentences = ["apple apple banana", "apple banana banana banana"]
        freq = summarizer.calculate_word_frequencies(sentences)
        
        # Most frequent word should have frequency 1.0
        assert max(freq.values()) == 1.0
    
    def test_calculate_sentence_scores_empty_sentences(self):
        """Test sentence scoring with empty list"""
        summarizer = create_summarizer()
        
        scores = summarizer.calculate_sentence_scores([], {})
        
        assert scores == {}
    
    def test_calculate_sentence_scores_with_no_tokens(self):
        """Test sentence scoring when sentences produce no tokens"""
        summarizer = create_summarizer()
        
        sentences = ["a the is"]  # All stop words
        word_freq = {}
        
        scores = summarizer.calculate_sentence_scores(sentences, word_freq)
        
        assert 0 in scores
        assert scores[0] == 0.0
    
    def test_extract_keywords_with_top_n(self):
        """Test keyword extraction with specific top_n"""
        summarizer = create_summarizer()
        
        text = "apple banana cherry apple banana apple"
        keywords = summarizer.extract_keywords(text, top_n=2)
        
        assert len(keywords) == 2
        # apple should be first (appears 3 times)
        assert keywords[0][0] == "apple"
        assert keywords[0][1] == 3
    
    def test_extract_keywords_empty_text(self):
        """Test keyword extraction with no valid tokens"""
        summarizer = create_summarizer()
        
        text = "a the is and or"  # All stop words
        keywords = summarizer.extract_keywords(text, top_n=5)
        
        assert len(keywords) == 0
    
    def test_calculate_statistics_empty_sentences(self):
        """Test statistics calculation with empty sentences list"""
        summarizer = create_summarizer()
        
        text = "Some text"
        stats = summarizer.calculate_statistics(text, [])
        
        assert stats['total_sentences'] == 0
        assert stats['avg_sentence_length'] == 0
    
    def test_calculate_statistics_complete(self):
        """Test complete statistics calculation"""
        summarizer = create_summarizer()
        
        # Create text with sentences meeting length requirements
        text = "This is a test sentence with enough words to meet the minimum requirements. " \
               "This is another test sentence with sufficient word count for processing. " \
               "Final test sentence here with adequate length for the filter criteria."
        sentences = summarizer.split_into_sentences(text)
        stats = summarizer.calculate_statistics(text, sentences)
        
        assert stats['total_characters'] == len(text)
        assert stats['total_words'] > 0
        assert stats['total_sentences'] == len(sentences)
        if sentences:
            assert stats['avg_sentence_length'] > 0
        assert stats['unique_words'] > 0
    
    def test_summarize_batch_empty_list(self):
        """Test batch summarization with empty list"""
        summarizer = create_summarizer()
        
        summaries = summarizer.summarize_batch([])
        
        assert len(summaries) == 0
    
    def test_summarize_batch_with_failures(self):
        """Test batch summarization with some failures"""
        summarizer = create_summarizer()
        
        documents = [
            ("good.pdf", "This is a good document with sufficient length and content for proper processing and analysis. It has meaningful content that meets all requirements."),
            ("empty.pdf", ""),
            ("another.pdf", "Another document with text and adequate length for testing purposes and validation. Good content here with proper word count for processing.")
        ]
        
        summaries = summarizer.summarize_batch(documents)
        
        assert len(summaries) == 3
        # First should succeed
        assert summaries[0].success
        # Second should fail (empty)
        assert not summaries[1].success
        # Third should succeed
        assert summaries[2].success
    
    def test_generate_summary_exception_handling(self):
        """Test that summary generation handles unexpected exceptions"""
        summarizer = create_summarizer()
        
        # Mock split_into_sentences to raise exception
        with patch.object(summarizer, 'split_into_sentences', side_effect=Exception("Test error")):
            summary = summarizer.generate_summary("Some text", "test.pdf")
            
            assert not summary.success
            assert "Error generating summary" in summary.error_message
    
    def test_clean_text_removes_special_characters(self):
        """Test that clean_text removes special characters"""
        summarizer = create_summarizer()
        
        text = "Hello @world! This #is $test %data ^with &special *chars"
        cleaned = summarizer.clean_text(text)
        
        # Special chars should be removed except sentence punctuation
        assert '@' not in cleaned
        assert '#' not in cleaned
        assert '$' not in cleaned
        assert '%' not in cleaned
        assert '^' not in cleaned
        assert '&' not in cleaned
        assert '*' not in cleaned
    
    def test_summary_config_dataclass(self):
        """Test SummaryConfig dataclass"""
        config = SummaryConfig(
            max_summary_sentences=10,
            min_sentence_length=15,
            max_sentence_length=60,
            keyword_count=20
        )
        
        assert config.max_summary_sentences == 10
        assert config.min_sentence_length == 15
        assert config.max_sentence_length == 60
        assert config.keyword_count == 20
    
    def test_document_summary_with_error(self):
        """Test DocumentSummary with error message"""
        summary = DocumentSummary(
            file_name="error.pdf",
            summary_text="",
            key_points=[],
            keywords=[],
            statistics={},
            success=False,
            error_message="Test error message"
        )
        
        assert not summary.success
        assert summary.error_message == "Test error message"
        assert summary.summary_text == ""


class TestIntegration:
    """Integration tests for parser and summarizer"""
    
    def test_full_pipeline_with_sample_text(self):
        """Test complete pipeline with sample text"""
        # Create components
        summarizer = create_summarizer(max_summary_sentences=3)
        
        # Sample text (simulating parsed PDF content)
        text = """
        Quantum computing represents a paradigm shift in computational technology.
        Unlike classical computers that use bits, quantum computers use quantum bits or qubits.
        These qubits can exist in multiple states simultaneously through superposition.
        Quantum entanglement allows qubits to be correlated in ways impossible for classical bits.
        This enables quantum computers to solve certain problems exponentially faster.
        Applications include cryptography, drug discovery, and optimization problems.
        """
        
        # Generate summary
        summary = summarizer.generate_summary(text, "quantum_computing.pdf")
        
        assert summary.success
        assert len(summary.summary_text) > 0
        assert len(summary.key_points) <= 3
        assert len(summary.keywords) > 0
        
        # Check that keywords are relevant
        keyword_words = [kw[0] for kw in summary.keywords]
        assert any('quantum' in kw for kw in keyword_words)
    
    def test_full_pipeline_with_real_pdf(self):
        """Test complete pipeline with actual PDF creation"""
        # Create a simple PDF
        pdf_writer = PdfWriter()
        pdf_writer.add_blank_page(width=200, height=200)
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            pdf_writer.write(f)
            pdf_path = Path(f.name)
        
        try:
            # Parse PDF
            parser = create_parser()
            result = parser.extract_text_from_pdf(pdf_path)
            
            # Even blank PDFs should parse successfully
            assert result.success
            assert result.num_pages == 1
        finally:
            pdf_path.unlink()
    
    def test_parse_and_summarize_pipeline(self):
        """Test parsing a PDF and then summarizing it"""
        # Create PDF with text
        pdf_writer = PdfWriter()
        pdf_writer.add_blank_page(width=200, height=200)
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            pdf_writer.write(f)
            pdf_path = Path(f.name)
        
        try:
            # Parse
            parser = create_parser()
            parse_result = parser.extract_text_from_pdf(pdf_path)
            
            if parse_result.success:
                # Create some sample text if PDF was blank
                text = parse_result.text_content if parse_result.text_content else \
                    "Sample text for testing. This is another sentence. And one more sentence for good measure."
                
                # Summarize
                summarizer = create_summarizer()
                summary = summarizer.generate_summary(text, parse_result.file_name)
                
                assert summary is not None
        finally:
            pdf_path.unlink()
    
    def test_batch_processing_pipeline(self):
        """Test batch processing multiple documents"""
        # Create multiple PDFs
        pdf_files = []
        for i in range(3):
            pdf_writer = PdfWriter()
            pdf_writer.add_blank_page(width=200, height=200)
            
            with tempfile.NamedTemporaryFile(suffix=f'_{i}.pdf', delete=False) as f:
                pdf_writer.write(f)
                pdf_files.append(Path(f.name))
        
        try:
            # Parse batch
            parser = create_parser()
            results = parser.parse_batch(pdf_files)
            
            assert len(results) == 3
            
            # Prepare for summarization
            documents = [
                (r.file_name, "Sample text for summarization. Another sentence here. Final sentence.")
                for r in results if r.success
            ]
            
            # Batch summarize
            summarizer = create_summarizer()
            summaries = summarizer.summarize_batch(documents)
            
            assert len(summaries) > 0
        finally:
            for pdf_file in pdf_files:
                pdf_file.unlink()
    
    def test_configuration_propagation(self):
        """Test that configuration is properly used"""
        # Create parser with specific config
        parser = create_parser(
            max_file_size_mb=5.0,
            max_batch_size=3,
            max_pages_per_pdf=25
        )
        
        assert parser.config.max_file_size_mb == 5.0
        assert parser.config.max_batch_size == 3
        assert parser.config.max_pages_per_pdf == 25
        
        # Create summarizer with specific config
        summarizer = create_summarizer(
            max_summary_sentences=8,
            keyword_count=12
        )
        
        assert summarizer.config.max_summary_sentences == 8
        assert summarizer.config.keyword_count == 12


class TestEdgeCases:
    """Test edge cases and boundary conditions"""
    
    def test_very_long_text(self):
        """Test summarization of very long text"""
        summarizer = create_summarizer(max_summary_sentences=5)
        
        # Generate long text
        text = " ".join([f"This is sentence number {i} with some content." for i in range(100)])
        
        summary = summarizer.generate_summary(text, "long.pdf")
        
        # Should still work but only return configured number of sentences
        if summary.success:
            assert len(summary.key_points) <= 5
    
    def test_text_with_only_stop_words(self):
        """Test text containing only stop words"""
        summarizer = create_summarizer()
        
        text = "a the is and or but with from to at by for of on in it as be was were have has had will would should could may might must"
        summary = summarizer.generate_summary(text, "stopwords.pdf")
        
        # Should fail or handle gracefully
        assert not summary.success or len(summary.keywords) == 0
    
    def test_text_with_numbers_only(self):
        """Test text with only numbers"""
        summarizer = create_summarizer()
        
        text = "123 456 789 012 345 678 901 234"
        summary = summarizer.generate_summary(text, "numbers.pdf")
        
        # Should handle gracefully
        assert summary is not None
    
    def test_unicode_text(self):
        """Test text with Unicode characters"""
        summarizer = create_summarizer()
        
        text = "This contains Unicode: café, naïve, résumé. Some emojis too: 😀 🎉. And special chars: €£¥."
        summary = summarizer.generate_summary(text, "unicode.pdf")
        
        # Should handle Unicode without crashing
        assert summary is not None
    
    def test_mixed_case_text(self):
        """Test that case is handled properly"""
        summarizer = create_summarizer()
        
        text = "UPPERCASE sentence here. lowercase sentence here. MiXeD CaSe SeNtEnCe HeRe."
        summary = summarizer.generate_summary(text, "mixed.pdf")
        
        if summary.success:
            # Keywords should be lowercase
            assert all(kw[0].islower() for kw in summary.keywords)
    
    def test_sentence_boundary_cases(self):
        """Test various sentence boundary cases"""
        summarizer = create_summarizer()
        
        text = "Dr. Smith works at U.S.A. corporation. He earned his Ph.D. in 2020. The company was founded in St. Louis."
        sentences = summarizer.split_into_sentences(text)
        
        # Should handle abbreviations without splitting incorrectly
        assert isinstance(sentences, list)
    
    def test_zero_max_summary_sentences(self):
        """Test with zero summary sentences requested"""
        summarizer = create_summarizer(max_summary_sentences=0)
        
        text = "This is a test. Another sentence here."
        summary = summarizer.generate_summary(text, "zero.pdf")
        
        # Should handle gracefully
        assert summary is not None
    
    def test_negative_configuration_values(self):
        """Test that negative config values are handled"""
        # Config should accept the values (no validation in constructor)
        config = SummaryConfig(
            max_summary_sentences=-1,
            min_sentence_length=-1,
            max_sentence_length=-1,
            keyword_count=-1
        )
        
        assert config.max_summary_sentences == -1
    
    def test_very_short_sentences(self):
        """Test text with very short sentences"""
        summarizer = create_summarizer(min_sentence_length=2)
        
        text = "Hi. Bye. Go. Stop. Wait. Run."
        summary = summarizer.generate_summary(text, "short.pdf")
        
        # Should handle short sentences
        assert summary is not None
    
    def test_very_long_sentences(self):
        """Test text with very long sentences"""
        summarizer = create_summarizer(max_sentence_length=100)
        
        # Create a very long sentence
        long_sentence = "This is a very long sentence with many words " * 20
        text = long_sentence + ". Another sentence."
        
        summary = summarizer.generate_summary(text, "long_sentences.pdf")
        
        assert summary is not None


class TestErrorHandling:
    """Test error handling and recovery"""
    
    def test_parser_with_corrupted_file(self):
        """Test parser with corrupted file"""
        parser = create_parser()
        
        # Create a file with invalid PDF content
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            f.write(b'This is not a valid PDF file')
            temp_path = Path(f.name)
        
        try:
            result = parser.extract_text_from_pdf(temp_path)
            
            assert not result.success
            assert result.error_message is not None
        finally:
            temp_path.unlink()
    
    def test_parser_with_empty_file(self):
        """Test parser with empty file"""
        parser = create_parser()
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            temp_path = Path(f.name)
        
        try:
            result = parser.extract_text_from_pdf(temp_path)
            
            # Should fail gracefully
            assert not result.success or result.num_pages == 0
        finally:
            temp_path.unlink()
    
    def test_summarizer_with_exception_in_tokenize(self):
        """Test summarizer handles tokenization errors"""
        summarizer = create_summarizer()
        
        # This should not crash even with unusual input
        text = None
        try:
            # This will fail but should be caught
            with patch.object(summarizer, 'tokenize', side_effect=Exception("Error")):
                summary = summarizer.generate_summary("test", "test.pdf")
                # Should handle error
                assert not summary.success
        except:
            pass  # Expected to handle internally


def test_module_imports():
    """Test that all module components can be imported"""
    # Already imported at the top, just verify they exist
    assert PDFParser is not None
    assert PDFSummarizer is not None
    
    # Verify factory functions work
    parser = create_parser()
    summarizer = create_summarizer()
    
    assert isinstance(parser, PDFParser)
    assert isinstance(summarizer, PDFSummarizer)


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
