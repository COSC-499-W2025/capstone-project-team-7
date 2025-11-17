"""
Document Analyzer Module
Handles analysis of text-based documents (.md, .txt, .docx, etc.)
Reuses PDF summarizer for consistent text analysis
"""
import re
from pathlib import Path
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass
from collections import Counter
import logging

# Import the existing PDF summarizer
from .pdf_summarizer import create_summarizer, SummaryConfig

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


@dataclass
class DocumentConfig:
    """Configuration for document analysis"""
    max_file_size_mb: float = 10.0  # Maximum file size in MB
    max_batch_size: int = 20  # Maximum documents per batch
    encoding: str = 'utf-8'  # Default file encoding
    fallback_encodings: Optional[List[str]] = None  # Fallback encodings to try
    
    def __post_init__(self):
        if self.fallback_encodings is None:
            self.fallback_encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']


@dataclass
class DocumentMetadata:
    """Metadata extracted from document"""
    file_type: str
    word_count: int
    character_count: int
    line_count: int
    paragraph_count: int
    reading_time_minutes: float
    language_detected: Optional[str] = None
    # Markdown-specific
    heading_count: int = 0
    headings: Optional[List[str]] = None
    code_blocks: int = 0
    links: int = 0
    images: int = 0
    # DOCX-specific
    pages: Optional[int] = None
    sections: Optional[int] = None
    
    def __post_init__(self):
        if self.headings is None:
            self.headings = []


@dataclass
class DocumentAnalysisResult:
    """Result of document analysis"""
    file_name: str
    file_type: str
    success: bool
    text_content: str = ""
    metadata: Optional[DocumentMetadata] = None
    summary: Optional[str] = None
    key_topics: Optional[List[str]] = None
    keywords: Optional[List[Tuple[str, int]]] = None
    statistics: Optional[Dict[str, Any]] = None
    file_size_mb: float = 0.0
    error_message: Optional[str] = None
    
    def __post_init__(self):
        if self.key_topics is None:
            self.key_topics = []
        if self.keywords is None:
            self.keywords = []
        if self.statistics is None:
            self.statistics = {}


class DocumentAnalyzer:
    """
    Analyzes text-based documents with support for multiple formats
    """
    
    SUPPORTED_EXTENSIONS = {'.txt', '.md', '.markdown', '.rst', '.log'}
    
    def __init__(self, config: Optional[DocumentConfig] = None):
        """
        Initialize document analyzer
        
        Args:
            config: DocumentConfig instance
        """
        self.config = config or DocumentConfig()
        
        # Initialize summarizer for text analysis
        self.summarizer = create_summarizer(
            max_summary_sentences=5,
            keyword_count=15
        )
        
        logger.info(f"DocumentAnalyzer initialized with config: {self.config}")
    
    def _read_file_with_encoding(self, file_path: Path) -> Tuple[str, str]:
        """
        Read file with automatic encoding detection
        
        Args:
            file_path: Path to file
            
        Returns:
            Tuple of (content, encoding_used)
        """
        encodings = self.config.fallback_encodings or ['utf-8', 'latin-1', 'cp1252']
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    content = f.read()
                logger.info(f"Successfully read {file_path.name} with encoding: {encoding}")
                return content, encoding
            except (UnicodeDecodeError, LookupError):
                continue
        
        # If all encodings fail, read as binary and decode with errors='ignore'
        with open(file_path, 'rb') as f:
            content = f.read().decode('utf-8', errors='ignore')
        logger.warning(f"Used fallback binary read for {file_path.name}")
        return content, 'utf-8 (with errors ignored)'
    
    def validate_file_size(self, file_path: Path) -> Tuple[bool, float, Optional[str]]:
        """
        Validate file size
        
        Args:
            file_path: Path to file
            
        Returns:
            Tuple of (is_valid, size_in_mb, error_message)
        """
        try:
            file_size_bytes = file_path.stat().st_size
            file_size_mb = file_size_bytes / (1024 * 1024)
            
            if file_size_mb > self.config.max_file_size_mb:
                error_msg = f"File size {file_size_mb:.2f}MB exceeds limit of {self.config.max_file_size_mb}MB"
                logger.warning(f"{file_path.name}: {error_msg}")
                return False, file_size_mb, error_msg
            
            return True, file_size_mb, None
        except Exception as e:
            error_msg = f"Error checking file size: {str(e)}"
            logger.error(f"{file_path.name}: {error_msg}")
            return False, 0.0, error_msg
    
    def _extract_markdown_features(self, content: str) -> Dict[str, Any]:
        """
        Extract Markdown-specific features
        
        Args:
            content: Markdown content
            
        Returns:
            Dictionary of Markdown features
        """
        features = {
            'headings': [],
            'heading_count': 0,
            'code_blocks': 0,
            'links': 0,
            'images': 0,
        }
        
        # Extract headings (# Header)
        heading_pattern = r'^(#{1,6})\s+(.+)$'
        for match in re.finditer(heading_pattern, content, re.MULTILINE):
            level = len(match.group(1))
            heading_text = match.group(2).strip()
            features['headings'].append(f"{'  ' * (level-1)}{heading_text}")
            features['heading_count'] += 1
        
        # Count code blocks (``` or indented)
        code_block_pattern = r'```[\s\S]*?```|^(?:    |\t).+$'
        features['code_blocks'] = len(re.findall(code_block_pattern, content, re.MULTILINE))
        
        # Count links [text](url)
        link_pattern = r'\[([^\]]+)\]\(([^\)]+)\)'
        features['links'] = len(re.findall(link_pattern, content))
        
        # Count images ![alt](url)
        image_pattern = r'!\[([^\]]*)\]\(([^\)]+)\)'
        features['images'] = len(re.findall(image_pattern, content))
        
        return features
    
    def _calculate_metadata(self, content: str, file_type: str) -> DocumentMetadata:
        """
        Calculate document metadata
        
        Args:
            content: Document content
            file_type: File extension
            
        Returns:
            DocumentMetadata object
        """
        # Basic counts
        character_count = len(content)
        word_count = len(content.split())
        line_count = len(content.splitlines())
        
        # Paragraph count (separated by blank lines or double newlines)
        # Split by multiple consecutive newlines (blank lines)
        paragraphs = re.split(r'\n\s*\n', content)
        # Filter out empty paragraphs
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
        paragraph_count = len(paragraphs) if paragraphs else 1
        
        # Reading time (average reading speed: 200 words/minute)
        reading_time_minutes = word_count / 200.0
        
        # Initialize metadata
        metadata = DocumentMetadata(
            file_type=file_type,
            word_count=word_count,
            character_count=character_count,
            line_count=line_count,
            paragraph_count=paragraph_count,
            reading_time_minutes=reading_time_minutes
        )
        
        # Extract Markdown-specific features
        if file_type in ['.md', '.markdown']:
            md_features = self._extract_markdown_features(content)
            metadata.heading_count = md_features['heading_count']
            metadata.headings = md_features['headings']
            metadata.code_blocks = md_features['code_blocks']
            metadata.links = md_features['links']
            metadata.images = md_features['images']
        
        return metadata
    
    def _extract_key_topics(self, content: str, metadata: DocumentMetadata) -> List[str]:
        """
        Extract key topics from document
        
        Args:
            content: Document content
            metadata: Document metadata
            
        Returns:
            List of key topics
        """
        topics = []
        
        # For Markdown, use headings as topics
        if metadata.headings:
            # Get top-level headings as main topics
            topics = [h.strip() for h in metadata.headings[:10]]
        
        # If no headings or not enough topics, extract from first paragraph
        if len(topics) < 3:
            paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
            if paragraphs:
                first_para = paragraphs[0]
                # Extract capitalized phrases as potential topics
                capitalized = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', first_para)
                topics.extend(capitalized[:5])
        
        # Remove duplicates while preserving order
        seen = set()
        unique_topics = []
        for topic in topics:
            if topic.lower() not in seen:
                seen.add(topic.lower())
                unique_topics.append(topic)
        
        return unique_topics[:10]
    
    def _extract_keywords_fallback(self, content: str) -> List[Tuple[str, int]]:
        """
        Extract keywords manually when summarizer fails
        
        Args:
            content: Document content
            
        Returns:
            List of (keyword, frequency) tuples
        """
        # Simple keyword extraction using word frequency
        words = re.findall(r'\b\w+\b', content.lower())
        
        # Filter out common stop words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
            'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'could', 'should', 'may', 'might', 'can', 'this', 'that', 'these',
            'those', 'it', 'its', 'they', 'their', 'them'
        }
        
        # Count word frequencies
        from collections import Counter
        word_freq = Counter(w for w in words if w not in stop_words and len(w) > 3)
        
        # Return top keywords
        return word_freq.most_common(15)
    
    def analyze_document(self, file_path: Path) -> DocumentAnalysisResult:
        """
        Analyze a document file
        
        Args:
            file_path: Path to document file
            
        Returns:
            DocumentAnalysisResult with analysis results
        """
        file_name = file_path.name
        file_type = file_path.suffix.lower()
        
        result = DocumentAnalysisResult(
            file_name=file_name,
            file_type=file_type,
            success=False
        )
        
        try:
            # Validate file type
            if file_type not in self.SUPPORTED_EXTENSIONS:
                result.error_message = f"Unsupported file type: {file_type}"
                logger.warning(f"{file_name}: {result.error_message}")
                return result
            
            # Validate file size
            is_valid, file_size_mb, error_msg = self.validate_file_size(file_path)
            result.file_size_mb = file_size_mb
            
            if not is_valid:
                result.error_message = error_msg
                return result
            
            # Read file content
            content, encoding = self._read_file_with_encoding(file_path)
            result.text_content = content
            
            if not content.strip():
                result.error_message = "Empty document"
                logger.warning(f"{file_name}: Empty content")
                return result
            
            # Calculate metadata
            metadata = self._calculate_metadata(content, file_type)
            result.metadata = metadata
            
            # Generate summary using existing PDF summarizer
            summary_result = self.summarizer.generate_summary(content, file_name)
            
            if summary_result.success:
                result.summary = summary_result.summary_text
                result.keywords = summary_result.keywords
                result.statistics = summary_result.statistics
            else:
                logger.warning(f"{file_name}: Summary generation failed - {summary_result.error_message}")
                # Even if summary fails, extract basic keywords manually
                result.summary = ""
                result.keywords = self._extract_keywords_fallback(content)
                result.statistics = {
                    'total_words': metadata.word_count,
                    'total_sentences': len([s for s in content.split('.') if s.strip()]),
                    'unique_words': len(set(content.lower().split()))
                }
            
            # Extract key topics
            result.key_topics = self._extract_key_topics(content, metadata)
            
            result.success = True
            logger.info(
                f"Successfully analyzed {file_name}: "
                f"{metadata.word_count} words, "
                f"{metadata.paragraph_count} paragraphs"
            )
            
        except Exception as e:
            error_msg = f"Error analyzing document: {str(e)}"
            logger.error(f"{file_name}: {error_msg}")
            result.error_message = error_msg
        
        return result
    
    def analyze_batch(self, file_paths: List[Path]) -> List[DocumentAnalysisResult]:
        """
        Analyze multiple documents
        
        Args:
            file_paths: List of file paths
            
        Returns:
            List of DocumentAnalysisResult objects
        """
        logger.info(f"Starting batch analysis of {len(file_paths)} documents")
        
        # Validate batch size
        if len(file_paths) > self.config.max_batch_size:
            logger.warning(
                f"Batch size {len(file_paths)} exceeds limit {self.config.max_batch_size}, "
                f"processing first {self.config.max_batch_size} files"
            )
            file_paths = file_paths[:self.config.max_batch_size]
        
        results = []
        for file_path in file_paths:
            result = self.analyze_document(file_path)
            results.append(result)
        
        successful = sum(1 for r in results if r.success)
        logger.info(f"Batch analysis complete: {successful}/{len(results)} successful")
        
        return results
    
    def analyze_from_text(self, text: str, file_name: str = "text_input") -> DocumentAnalysisResult:
        """
        Analyze text content directly (without file)
        
        Args:
            text: Text content to analyze
            file_name: Name for the analysis result (can include extension to infer type)
            
        Returns:
            DocumentAnalysisResult with analysis results
        """
        # Infer file type from filename extension if provided
        file_type = Path(file_name).suffix.lower() if '.' in file_name else '.txt'
        if not file_type:
            file_type = '.txt'
        
        result = DocumentAnalysisResult(
            file_name=file_name,
            file_type=file_type,
            success=False
        )
        
        try:
            if not text.strip():
                result.error_message = "Empty text provided"
                return result
            
            result.text_content = text
            
            # Calculate metadata
            metadata = self._calculate_metadata(text, file_type)
            result.metadata = metadata
            
            # Generate summary
            summary_result = self.summarizer.generate_summary(text, file_name)
            
            if summary_result.success:
                result.summary = summary_result.summary_text
                result.keywords = summary_result.keywords
                result.statistics = summary_result.statistics
            else:
                # Set empty values instead of None when summary fails
                logger.warning(f"{file_name}: Summary generation failed - {summary_result.error_message}")
                result.summary = ""
                result.keywords = self._extract_keywords_fallback(text)
                result.statistics = {
                    'total_words': metadata.word_count,
                    'total_sentences': len([s for s in text.split('.') if s.strip()]),
                    'unique_words': len(set(text.lower().split()))
                }
            
            # Extract key topics
            result.key_topics = self._extract_key_topics(text, metadata)
            
            result.success = True
            logger.info(f"Successfully analyzed text input: {metadata.word_count} words")
            
        except Exception as e:
            error_msg = f"Error analyzing text: {str(e)}"
            logger.error(error_msg)
            result.error_message = error_msg
        
        return result
    
    def to_json(self, result: DocumentAnalysisResult) -> Dict[str, Any]:
        """
        Convert analysis result to JSON-serializable dictionary
        
        Args:
            result: DocumentAnalysisResult to convert
            
        Returns:
            Dictionary with analysis results
        """
        json_data = {
            'file_name': result.file_name,
            'file_type': result.file_type,
            'success': result.success,
            'file_size_mb': result.file_size_mb,
        }
        
        if result.success and result.metadata:
            json_data.update({
                'metadata': {
                    'word_count': result.metadata.word_count,
                    'character_count': result.metadata.character_count,
                    'line_count': result.metadata.line_count,
                    'paragraph_count': result.metadata.paragraph_count,
                    'reading_time_minutes': round(result.metadata.reading_time_minutes, 2),
                },
                'summary': result.summary,
                'key_topics': result.key_topics or [],
                'keywords': [{'word': k, 'frequency': f} for k, f in (result.keywords or [])],
                'statistics': result.statistics or {},
            })
            
            # Add format-specific metadata
            if result.file_type in ['.md', '.markdown']:
                json_data['metadata']['markdown'] = {
                    'heading_count': result.metadata.heading_count,
                    'headings': result.metadata.headings,
                    'code_blocks': result.metadata.code_blocks,
                    'links': result.metadata.links,
                    'images': result.metadata.images,
                }
        else:
            json_data['error'] = result.error_message
        
        return json_data


def create_analyzer(
    max_file_size_mb: float = 10.0,
    max_batch_size: int = 20,
    encoding: str = 'utf-8'
) -> DocumentAnalyzer:
    """
    Factory function to create a DocumentAnalyzer
    
    Args:
        max_file_size_mb: Maximum file size in MB
        max_batch_size: Maximum documents per batch
        encoding: Default file encoding
        
    Returns:
        Configured DocumentAnalyzer instance
    """
    config = DocumentConfig(
        max_file_size_mb=max_file_size_mb,
        max_batch_size=max_batch_size,
        encoding=encoding
    )
    return DocumentAnalyzer(config)
