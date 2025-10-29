"""
Tests for Document Analyzer
Comprehensive test suite for document analysis
"""
import pytest
import tempfile
from pathlib import Path
from conftest import import_from_local_analysis

# Import modules from local-analysis directory using conftest helper
document_analyzer = import_from_local_analysis('document_analyzer')
DocumentAnalyzer = document_analyzer.DocumentAnalyzer
DocumentConfig = document_analyzer.DocumentConfig
DocumentMetadata = document_analyzer.DocumentMetadata
DocumentAnalysisResult = document_analyzer.DocumentAnalysisResult
create_analyzer = document_analyzer.create_analyzer


class TestDocumentAnalyzer:
    """Test cases for DocumentAnalyzer"""
    
    def test_create_analyzer_with_defaults(self):
        """Test creating analyzer with default configuration"""
        analyzer = create_analyzer()
        assert analyzer is not None
        assert isinstance(analyzer, DocumentAnalyzer)
        assert analyzer.config.max_file_size_mb == 10.0
        assert analyzer.config.max_batch_size == 20
    
    def test_create_analyzer_with_custom_config(self):
        """Test creating analyzer with custom configuration"""
        analyzer = create_analyzer(
            max_file_size_mb=5.0,
            max_batch_size=10,
            encoding='latin-1'
        )
        assert analyzer.config.max_file_size_mb == 5.0
        assert analyzer.config.max_batch_size == 10
        assert analyzer.config.encoding == 'latin-1'
    
    def test_analyze_txt_file(self):
        """Test analyzing a plain text file"""
        analyzer = create_analyzer()
        
        # Create temporary file
        content = """
        This is a test document with multiple paragraphs.
        It contains several sentences for analysis.
        
        This is the second paragraph with more content.
        We want to test the document analyzer capabilities.
        """
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(content)
            temp_path = Path(f.name)
        
        try:
            result = analyzer.analyze_document(temp_path)
            
            assert result.success is True
            assert result.file_type == '.txt'
            assert result.metadata.word_count > 0
            assert result.metadata.paragraph_count >= 2
            assert result.summary is not None
            assert len(result.keywords) > 0
        finally:
            temp_path.unlink()
    
    def test_analyze_markdown_file(self):
        """Test analyzing a Markdown file"""
        analyzer = create_analyzer()
        
        markdown_content = """
# Main Heading

This is an introduction paragraph.

## Section 1

This is content in section 1 with some **bold text**.

### Subsection 1.1

More content here with [a link](https://example.com).

## Section 2

```python
def hello():
    print("Hello, World!")
```

![Image](image.png)

Final paragraph with some text.
        """
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
            f.write(markdown_content)
            temp_path = Path(f.name)
        
        try:
            result = analyzer.analyze_document(temp_path)
            
            assert result.success is True
            assert result.file_type == '.md'
            assert result.metadata.heading_count >= 4
            assert len(result.metadata.headings) >= 4
            assert result.metadata.code_blocks >= 1
            assert result.metadata.links >= 1
            assert result.metadata.images >= 1
            assert result.metadata.word_count > 0
        finally:
            temp_path.unlink()
    
    def test_analyze_empty_file(self):
        """Test analyzing an empty file"""
        analyzer = create_analyzer()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("")
            temp_path = Path(f.name)
        
        try:
            result = analyzer.analyze_document(temp_path)
            
            assert result.success is False
            assert "Empty document" in result.error_message
        finally:
            temp_path.unlink()
    
    def test_analyze_unsupported_file_type(self):
        """Test analyzing unsupported file type"""
        analyzer = create_analyzer()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xyz', delete=False) as f:
            f.write("content")
            temp_path = Path(f.name)
        
        try:
            result = analyzer.analyze_document(temp_path)
            
            assert result.success is False
            assert "Unsupported file type" in result.error_message
        finally:
            temp_path.unlink()
    
    def test_file_size_validation(self):
        """Test file size validation"""
        analyzer = create_analyzer(max_file_size_mb=0.001)  # 1 KB limit
        
        # Create file larger than limit
        large_content = "a" * 2000  # 2 KB
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(large_content)
            temp_path = Path(f.name)
        
        try:
            result = analyzer.analyze_document(temp_path)
            
            assert result.success is False
            assert "exceeds limit" in result.error_message.lower()
        finally:
            temp_path.unlink()
    
    def test_analyze_from_text(self):
        """Test analyzing text directly"""
        analyzer = create_analyzer()
        
        text = """
        Artificial intelligence is transforming technology.
        Machine learning enables computers to learn from data.
        
        Deep learning uses neural networks for complex tasks.
        Natural language processing helps understand human language.
        """
        
        result = analyzer.analyze_from_text(text, "test_input.txt")
        
        assert result.success is True
        assert result.file_name == "test_input.txt"
        assert result.metadata.word_count > 0
        assert result.summary is not None
        assert len(result.keywords) > 0
    
    def test_analyze_from_empty_text(self):
        """Test analyzing empty text"""
        analyzer = create_analyzer()
        
        result = analyzer.analyze_from_text("", "empty.txt")
        
        assert result.success is False
        assert "Empty text" in result.error_message
    
    def test_batch_analysis(self):
        """Test batch document analysis"""
        analyzer = create_analyzer()
        
        # Create multiple temporary files
        files = []
        for i in range(3):
            content = f"This is document number {i}. It has some content for testing purposes."
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(content)
                files.append(Path(f.name))
        
        try:
            results = analyzer.analyze_batch(files)
            
            assert len(results) == 3
            assert all(isinstance(r, DocumentAnalysisResult) for r in results)
            assert sum(1 for r in results if r.success) >= 2
        finally:
            for file_path in files:
                file_path.unlink()
    
    def test_batch_size_limit(self):
        """Test batch size limit enforcement"""
        analyzer = create_analyzer(max_batch_size=2)
        
        # Create more files than batch limit
        files = []
        for i in range(5):
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(f"Content {i}")
                files.append(Path(f.name))
        
        try:
            results = analyzer.analyze_batch(files)
            
            # Should only process first 2 files
            assert len(results) == 2
        finally:
            for file_path in files:
                file_path.unlink()
    
    def test_metadata_calculation(self):
        """Test metadata calculation"""
        analyzer = create_analyzer()
        
        content = """Line 1
Line 2
Line 3

Paragraph 2 with multiple words here.

Paragraph 3.
"""
        
        result = analyzer.analyze_from_text(content, "metadata_test.txt")
        
        assert result.success is True
        assert result.metadata.line_count >= 7
        assert result.metadata.paragraph_count == 3
        assert result.metadata.word_count > 0
        assert result.metadata.character_count == len(content)
        assert result.metadata.reading_time_minutes > 0
    
    def test_to_json_conversion(self):
        """Test converting result to JSON"""
        analyzer = create_analyzer()
        
        text = "This is a simple test document."
        result = analyzer.analyze_from_text(text, "json_test.txt")
        
        json_data = analyzer.to_json(result)
        
        assert 'file_name' in json_data
        assert 'file_type' in json_data
        assert 'success' in json_data
        assert 'metadata' in json_data
        assert 'summary' in json_data
        assert 'keywords' in json_data
        assert json_data['success'] is True
        
        # Check metadata structure
        assert 'word_count' in json_data['metadata']
        assert 'reading_time_minutes' in json_data['metadata']
    
    def test_markdown_heading_extraction(self):
        """Test Markdown heading extraction"""
        analyzer = create_analyzer()
        
        markdown = """
# Title
## Subtitle
### Section
#### Subsection
        """
        
        result = analyzer.analyze_from_text(markdown, "headings.md")
        
        assert result.success is True
        assert result.metadata.heading_count == 4
        assert len(result.metadata.headings) == 4
    
    def test_key_topics_extraction(self):
        """Test key topics extraction"""
        analyzer = create_analyzer()
        
        markdown = """
# Machine Learning Introduction

Machine Learning is a subset of Artificial Intelligence.

## Deep Learning

Deep Learning uses neural networks.

## Natural Language Processing

NLP helps computers understand human language.
        """
        
        result = analyzer.analyze_from_text(markdown, "topics.md")
        
        assert result.success is True
        assert len(result.key_topics) > 0
        # Should extract headings as topics
        assert any('Machine Learning' in topic or 'Deep Learning' in topic for topic in result.key_topics)
    
    def test_encoding_fallback(self):
        """Test encoding fallback mechanism"""
        analyzer = create_analyzer()
        
        # Create file with special characters
        content = "Hello world with special chars: café, naïve, résumé"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(content)
            temp_path = Path(f.name)
        
        try:
            result = analyzer.analyze_document(temp_path)
            
            assert result.success is True
            assert result.text_content is not None
        finally:
            temp_path.unlink()
    
    def test_reading_time_calculation(self):
        """Test reading time calculation"""
        analyzer = create_analyzer()
        
        # 200 words should be ~1 minute reading time
        words = ["word"] * 200
        content = " ".join(words)
        
        result = analyzer.analyze_from_text(content, "reading_time.txt")
        
        assert result.success is True
        assert abs(result.metadata.reading_time_minutes - 1.0) < 0.1
    
    def test_statistics_generation(self):
        """Test statistics generation from summarizer"""
        analyzer = create_analyzer()
        
        text = """
        This is a test document with enough content for proper analysis.
        It has multiple sentences to ensure the summarizer works correctly.
        The statistics should include word counts and sentence information.
        We need sufficient text for meaningful statistical analysis.
        """
        
        result = analyzer.analyze_from_text(text, "stats.txt")
        
        assert result.success is True
        assert result.statistics is not None
        assert 'total_words' in result.statistics
        assert 'total_sentences' in result.statistics


class TestDocumentMetadata:
    """Test DocumentMetadata dataclass"""
    
    def test_metadata_creation(self):
        """Test creating DocumentMetadata"""
        metadata = DocumentMetadata(
            file_type='.txt',
            word_count=100,
            character_count=500,
            line_count=10,
            paragraph_count=3,
            reading_time_minutes=0.5
        )
        
        assert metadata.file_type == '.txt'
        assert metadata.word_count == 100
        assert metadata.reading_time_minutes == 0.5
        assert metadata.headings == []  # Default
    
    def test_markdown_metadata(self):
        """Test Markdown-specific metadata"""
        metadata = DocumentMetadata(
            file_type='.md',
            word_count=100,
            character_count=500,
            line_count=10,
            paragraph_count=3,
            reading_time_minutes=0.5,
            heading_count=5,
            headings=['Title', 'Section 1', 'Section 2'],
            code_blocks=2,
            links=3,
            images=1
        )
        
        assert metadata.heading_count == 5
        assert len(metadata.headings) == 3
        assert metadata.code_blocks == 2
        assert metadata.links == 3
        assert metadata.images == 1


class TestEdgeCases:
    """Test edge cases"""
    
    def test_very_long_document(self):
        """Test analyzing a very long document"""
        analyzer = create_analyzer()
        
        # Create a long document
        long_content = ("This is a sentence with enough words to pass filters. " * 100)
        
        result = analyzer.analyze_from_text(long_content, "long_doc.txt")
        
        assert result.success is True
        assert result.metadata.word_count > 500
    
    def test_special_characters(self):
        """Test document with special characters"""
        analyzer = create_analyzer()
        
        content = "Special chars: @#$%^&*() and emojis 🎉 🚀"
        
        result = analyzer.analyze_from_text(content, "special.txt")
        
        assert result.success is True
    
    def test_multiple_blank_lines(self):
        """Test document with multiple blank lines"""
        analyzer = create_analyzer()
        
        content = "Paragraph 1\n\n\n\n\nParagraph 2\n\n\n\nParagraph 3"
        
        result = analyzer.analyze_from_text(content, "blanks.txt")
        
        assert result.success is True
        assert result.metadata.paragraph_count == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
