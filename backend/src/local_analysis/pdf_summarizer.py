"""
PDF Summarizer Module
In-house text summarization without external LLM dependencies
Uses extractive summarization techniques
"""
import re
import math
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass
from collections import Counter, defaultdict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class SummaryConfig:
    """Configuration for summarization"""
    max_summary_sentences: int = 5  # Maximum sentences in summary
    min_sentence_length: int = 10  # Minimum words in a sentence
    max_sentence_length: int = 50  # Maximum words in a sentence
    keyword_count: int = 10  # Number of top keywords to extract


@dataclass
class DocumentSummary:
    """Summary result for a document"""
    file_name: str
    summary_text: str
    key_points: List[str]
    keywords: List[Tuple[str, int]]  # (keyword, frequency)
    statistics: Dict[str, Any]
    success: bool
    error_message: Optional[str] = None


class PDFSummarizer:
    """
    In-house PDF summarizer using extractive summarization
    Implements TF-IDF based sentence scoring
    """
    
    def __init__(self, config: Optional[SummaryConfig] = None):
        """
        Initialize summarizer with configuration
        
        Args:
            config: SummaryConfig instance
        """
        self.config = config or SummaryConfig()
        
        # Common English stop words (expanded list)
        self.stop_words = {
            'a', 'an', 'and', 'are', 'as', 'at', 'be', 'been', 'by', 'for',
            'from', 'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on', 'that',
            'the', 'to', 'was', 'were', 'will', 'with', 'this', 'but', 'they',
            'have', 'had', 'what', 'when', 'where', 'who', 'which', 'why', 'how',
            'can', 'could', 'would', 'should', 'may', 'might', 'must', 'shall',
            'i', 'you', 'we', 'our', 'your', 'their', 'my', 'his', 'her',
            'or', 'if', 'than', 'so', 'these', 'those', 'such', 'into', 'through',
            'during', 'before', 'after', 'above', 'below', 'between', 'under',
            'again', 'further', 'then', 'once', 'here', 'there', 'all', 'both',
            'each', 'few', 'more', 'most', 'other', 'some', 'any', 'no', 'nor',
            'not', 'only', 'own', 'same', 'too', 'very', 'just', 'now'
        }
        
        logger.info(f"PDFSummarizer initialized with config: {self.config}")
    
    def clean_text(self, text: str) -> str:
        """
        Clean and normalize text
        
        Args:
            text: Raw text to clean
            
        Returns:
            Cleaned text
        """
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove special characters but keep sentence punctuation
        text = re.sub(r'[^\w\s\.\,\!\?\;\:]', '', text)
        return text.strip()
    
    def split_into_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences
        
        Args:
            text: Text to split
            
        Returns:
            List of sentences
        """
        # Simple sentence splitting (handles common cases)
        text = self.clean_text(text)
        
        # Split on sentence endings
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        # Filter sentences by length
        filtered_sentences = []
        for sentence in sentences:
            word_count = len(sentence.split())
            if (self.config.min_sentence_length <= word_count <= 
                self.config.max_sentence_length):
                filtered_sentences.append(sentence.strip())
        
        return filtered_sentences
    
    def tokenize(self, text: str) -> List[str]:
        """
        Tokenize text into words, removing stop words
        
        Args:
            text: Text to tokenize
            
        Returns:
            List of tokens (words)
        """
        # Convert to lowercase and split
        words = text.lower().split()
        
        # Remove punctuation and filter stop words
        tokens = []
        for word in words:
            # Remove punctuation
            word = re.sub(r'[^\w]', '', word)
            if word and word not in self.stop_words and len(word) > 2:
                tokens.append(word)
        
        return tokens
    
    def calculate_word_frequencies(self, sentences: List[str]) -> Dict[str, float]:
        """
        Calculate normalized word frequencies (TF)
        
        Args:
            sentences: List of sentences
            
        Returns:
            Dictionary of word frequencies
        """
        # Count word occurrences
        word_freq = Counter()
        for sentence in sentences:
            tokens = self.tokenize(sentence)
            word_freq.update(tokens)
        
        # Normalize by maximum frequency
        if not word_freq:
            return {}
        
        max_freq = max(word_freq.values())
        normalized_freq = {
            word: freq / max_freq 
            for word, freq in word_freq.items()
        }
        
        return normalized_freq
    
    def calculate_sentence_scores(
        self, 
        sentences: List[str], 
        word_freq: Dict[str, float]
    ) -> Dict[int, float]:
        """
        Calculate importance scores for sentences
        
        Args:
            sentences: List of sentences
            word_freq: Word frequency dictionary
            
        Returns:
            Dictionary mapping sentence index to score
        """
        sentence_scores = {}
        
        for idx, sentence in enumerate(sentences):
            tokens = self.tokenize(sentence)
            
            if not tokens:
                sentence_scores[idx] = 0.0
                continue
            
            # Score is sum of word frequencies divided by sentence length
            score = sum(word_freq.get(token, 0) for token in tokens)
            sentence_scores[idx] = score / len(tokens)
        
        return sentence_scores
    
    def extract_keywords(
        self, 
        text: str, 
        top_n: Optional[int] = None
    ) -> List[Tuple[str, int]]:
        """
        Extract top keywords from text
        
        Args:
            text: Text to extract keywords from
            top_n: Number of top keywords to return
            
        Returns:
            List of (keyword, frequency) tuples
        """
        if top_n is None:
            top_n = self.config.keyword_count
        
        tokens = self.tokenize(text)
        word_freq = Counter(tokens)
        
        return word_freq.most_common(top_n)
    
    def calculate_statistics(self, text: str, sentences: List[str]) -> Dict[str, Any]:
        """
        Calculate document statistics
        
        Args:
            text: Full text
            sentences: List of sentences
            
        Returns:
            Dictionary of statistics
        """
        words = text.split()
        
        return {
            'total_characters': len(text),
            'total_words': len(words),
            'total_sentences': len(sentences),
            'avg_sentence_length': len(words) / len(sentences) if sentences else 0,
            'unique_words': len(set(self.tokenize(text)))
        }
    
    def generate_summary(
        self, 
        text: str, 
        file_name: str = "document"
    ) -> DocumentSummary:
        """
        Generate an extractive summary of the text
        
        Args:
            text: Full text to summarize
            file_name: Name of the source file
            
        Returns:
            DocumentSummary object with results
        """
        try:
            logger.info(f"Generating summary for {file_name}")
            
            # Check if text is empty
            if not text or len(text.strip()) == 0:
                return DocumentSummary(
                    file_name=file_name,
                    summary_text="",
                    key_points=[],
                    keywords=[],
                    statistics={},
                    success=False,
                    error_message="Empty text provided"
                )
            
            # Split into sentences
            sentences = self.split_into_sentences(text)
            
            if not sentences:
                return DocumentSummary(
                    file_name=file_name,
                    summary_text="",
                    key_points=[],
                    keywords=[],
                    statistics={},
                    success=False,
                    error_message="No valid sentences found in text"
                )
            
            # Calculate word frequencies
            word_freq = self.calculate_word_frequencies(sentences)
            
            # Calculate sentence scores
            sentence_scores = self.calculate_sentence_scores(sentences, word_freq)
            
            # Select top sentences for summary
            num_sentences = min(
                len(sentences), 
                self.config.max_summary_sentences
            )
            
            # Get indices of top-scored sentences
            top_sentence_indices = sorted(
                sentence_scores.keys(),
                key=lambda idx: sentence_scores[idx],
                reverse=True
            )[:num_sentences]
            
            # Sort indices to maintain original order in summary
            top_sentence_indices.sort()
            
            # Create summary
            summary_sentences = [sentences[idx] for idx in top_sentence_indices]
            summary_text = " ".join(summary_sentences)
            
            # Extract keywords
            keywords = self.extract_keywords(text)
            
            # Calculate statistics
            statistics = self.calculate_statistics(text, sentences)
            
            # Create key points (just the summary sentences as separate points)
            key_points = summary_sentences
            
            logger.info(
                f"Summary generated for {file_name}: "
                f"{len(summary_sentences)} sentences, "
                f"{len(keywords)} keywords"
            )
            
            return DocumentSummary(
                file_name=file_name,
                summary_text=summary_text,
                key_points=key_points,
                keywords=keywords,
                statistics=statistics,
                success=True
            )
            
        except Exception as e:
            error_msg = f"Error generating summary: {str(e)}"
            logger.error(f"{file_name}: {error_msg}")
            
            return DocumentSummary(
                file_name=file_name,
                summary_text="",
                key_points=[],
                keywords=[],
                statistics={},
                success=False,
                error_message=error_msg
            )
    
    def summarize_batch(
        self, 
        documents: List[Tuple[str, str]]
    ) -> List[DocumentSummary]:
        """
        Generate summaries for a batch of documents
        
        Args:
            documents: List of (file_name, text) tuples
            
        Returns:
            List of DocumentSummary objects
        """
        logger.info(f"Generating summaries for batch of {len(documents)} documents")
        
        summaries = []
        for file_name, text in documents:
            summary = self.generate_summary(text, file_name)
            summaries.append(summary)
        
        successful = sum(1 for s in summaries if s.success)
        logger.info(f"Batch summarization complete: {successful}/{len(summaries)} successful")
        
        return summaries


def create_summarizer(
    max_summary_sentences: int = 5,
    min_sentence_length: int = 10,
    max_sentence_length: int = 50,
    keyword_count: int = 10
) -> PDFSummarizer:
    """
    Factory function to create a PDFSummarizer with custom configuration
    
    Args:
        max_summary_sentences: Maximum sentences in summary
        min_sentence_length: Minimum words in a sentence
        max_sentence_length: Maximum words in a sentence
        keyword_count: Number of top keywords to extract
        
    Returns:
        Configured PDFSummarizer instance
    """
    config = SummaryConfig(
        max_summary_sentences=max_summary_sentences,
        min_sentence_length=min_sentence_length,
        max_sentence_length=max_sentence_length,
        keyword_count=keyword_count
    )
    return PDFSummarizer(config)
