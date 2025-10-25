"""
PDF Parser Module
Handles parsing of PDF documents with performance controls
"""
import io
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import PyPDF2
from PyPDF2 import PdfReader
import logging

# Ensure PdfReadError is available across PyPDF2 versions; fall back to a generic Exception subclass if not found
try:
    from PyPDF2.errors import PdfReadError
except ImportError:
    PdfReadError = Exception  # type: ignore

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class PDFConfig:
    """Configuration for PDF parsing constraints"""
    max_file_size_mb: float = 10.0  # Maximum size per PDF in MB
    max_batch_size: int = 10  # Maximum number of PDFs per batch
    max_total_batch_size_mb: float = 50.0  # Maximum total batch size in MB
    max_pages_per_pdf: int = 100  # Maximum pages to parse per PDF


@dataclass
class PDFMetadata:
    """Metadata extracted from PDF"""
    title: Optional[str] = None
    author: Optional[str] = None
    subject: Optional[str] = None
    creator: Optional[str] = None
    producer: Optional[str] = None
    creation_date: Optional[str] = None
    modification_date: Optional[str] = None
    num_pages: int = 0


@dataclass
class PDFParseResult:
    """Result of parsing a single PDF"""
    file_name: str
    success: bool
    metadata: Optional[PDFMetadata] = None
    text_content: str = ""
    num_pages: int = 0
    file_size_mb: float = 0.0
    error_message: Optional[str] = None


class PDFParser:
    """
    PDF Parser with performance controls and batch processing support
    """
    
    def __init__(self, config: Optional[PDFConfig] = None):
        """
        Initialize PDF parser with configuration
        
        Args:
            config: PDFConfig instance with parsing constraints
        """
        self.config = config or PDFConfig()
        logger.info(f"PDFParser initialized with config: {self.config}")
    
    def validate_file_size(self, file_path: Path) -> Tuple[bool, float, Optional[str]]:
        """
        Validate if file size is within limits
        
        Args:
            file_path: Path to the PDF file
            
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
    
    def validate_batch(self, file_paths: List[Path]) -> Tuple[bool, Optional[str]]:
        """
        Validate batch size and total size constraints
        
        Args:
            file_paths: List of PDF file paths
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check number of files
        if len(file_paths) > self.config.max_batch_size:
            error_msg = f"Batch contains {len(file_paths)} files, exceeds limit of {self.config.max_batch_size}"
            logger.warning(error_msg)
            return False, error_msg
        
        # Check total batch size
        total_size_mb = 0.0
        for file_path in file_paths:
            try:
                file_size_bytes = file_path.stat().st_size
                total_size_mb += file_size_bytes / (1024 * 1024)
            except Exception as e:
                logger.error(f"Error calculating size for {file_path.name}: {str(e)}")
        
        if total_size_mb > self.config.max_total_batch_size_mb:
            error_msg = f"Total batch size {total_size_mb:.2f}MB exceeds limit of {self.config.max_total_batch_size_mb}MB"
            logger.warning(error_msg)
            return False, error_msg
        
        return True, None
    
    def extract_metadata(self, pdf_reader: PdfReader) -> PDFMetadata:
        """
        Extract metadata from PDF reader object
        
        Args:
            pdf_reader: PyPDF2 PdfReader object
            
        Returns:
            PDFMetadata object with extracted information
        """
        metadata = PDFMetadata(num_pages=len(pdf_reader.pages))
        
        if pdf_reader.metadata:
            try:
                metadata.title = pdf_reader.metadata.get('/Title', None)
                metadata.author = pdf_reader.metadata.get('/Author', None)
                metadata.subject = pdf_reader.metadata.get('/Subject', None)
                metadata.creator = pdf_reader.metadata.get('/Creator', None)
                metadata.producer = pdf_reader.metadata.get('/Producer', None)
                metadata.creation_date = pdf_reader.metadata.get('/CreationDate', None)
                metadata.modification_date = pdf_reader.metadata.get('/ModDate', None)
            except Exception as e:
                logger.warning(f"Error extracting metadata: {str(e)}")
        
        return metadata
    
    def extract_text_from_pdf(self, file_path: Path) -> PDFParseResult:
        """
        Extract text content from a single PDF file
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            PDFParseResult with extracted content and metadata
        """
        result = PDFParseResult(file_name=file_path.name, success=False)
        
        try:
            # Validate file size
            is_valid, file_size_mb, error_msg = self.validate_file_size(file_path)
            result.file_size_mb = file_size_mb
            
            if not is_valid:
                result.error_message = error_msg
                return result
            
            # Open and read PDF
            with open(file_path, 'rb') as file:
                pdf_reader = PdfReader(file)
                
                # Extract metadata
                result.metadata = self.extract_metadata(pdf_reader)
                result.num_pages = len(pdf_reader.pages)
                
                # Check page limit
                pages_to_process = min(result.num_pages, self.config.max_pages_per_pdf)
                
                if result.num_pages > self.config.max_pages_per_pdf:
                    logger.warning(
                        f"{file_path.name}: PDF has {result.num_pages} pages, "
                        f"processing only first {self.config.max_pages_per_pdf}"
                    )
                
                # Extract text from pages
                text_parts = []
                for page_num in range(pages_to_process):
                    try:
                        page = pdf_reader.pages[page_num]
                        text = page.extract_text()
                        if text:
                            text_parts.append(text)
                    except Exception as e:
                        logger.error(f"Error extracting page {page_num + 1} from {file_path.name}: {str(e)}")
                        continue
                
                result.text_content = "\n\n".join(text_parts)
                result.success = True
                
                logger.info(f"Successfully parsed {file_path.name}: {result.num_pages} pages, {file_size_mb:.2f}MB")
                
        except PdfReadError as e:
            result.error_message = f"PDF read error: {str(e)}"
            logger.error(f"{file_path.name}: {result.error_message}")
        except Exception as e:
            result.error_message = f"Unexpected error: {str(e)}"
            logger.error(f"{file_path.name}: {result.error_message}")
        
        return result
    
    def parse_batch(self, file_paths: List[Path]) -> List[PDFParseResult]:
        """
        Parse a batch of PDF files
        
        Args:
            file_paths: List of paths to PDF files
            
        Returns:
            List of PDFParseResult objects
        """
        logger.info(f"Starting batch parse of {len(file_paths)} PDFs")
        
        # Validate batch constraints
        is_valid, error_msg = self.validate_batch(file_paths)
        if not is_valid:
            # Return error result for all files
            return [
                PDFParseResult(
                    file_name=fp.name,
                    success=False,
                    error_message=f"Batch validation failed: {error_msg}"
                )
                for fp in file_paths
            ]
        
        # Process each file
        results = []
        for file_path in file_paths:
            result = self.extract_text_from_pdf(file_path)
            results.append(result)
        
        # Log summary
        successful = sum(1 for r in results if r.success)
        logger.info(f"Batch parse complete: {successful}/{len(results)} successful")
        
        return results
    
    def parse_from_bytes(self, pdf_bytes: bytes, file_name: str) -> PDFParseResult:
        """
        Parse PDF from bytes (useful for uploaded files)
        
        Args:
            pdf_bytes: PDF file content as bytes
            file_name: Name of the PDF file
            
        Returns:
            PDFParseResult with extracted content
        """
        result = PDFParseResult(file_name=file_name, success=False)
        
        try:
            # Check size
            file_size_mb = len(pdf_bytes) / (1024 * 1024)
            result.file_size_mb = file_size_mb
            
            if file_size_mb > self.config.max_file_size_mb:
                result.error_message = f"File size {file_size_mb:.2f}MB exceeds limit of {self.config.max_file_size_mb}MB"
                return result
            
            # Create file-like object from bytes
            pdf_file = io.BytesIO(pdf_bytes)
            pdf_reader = PdfReader(pdf_file)
            
            # Extract metadata
            result.metadata = self.extract_metadata(pdf_reader)
            result.num_pages = len(pdf_reader.pages)
            
            # Check page limit
            pages_to_process = min(result.num_pages, self.config.max_pages_per_pdf)
            
            # Extract text
            text_parts = []
            for page_num in range(pages_to_process):
                try:
                    page = pdf_reader.pages[page_num]
                    text = page.extract_text()
                    if text:
                        text_parts.append(text)
                except Exception as e:
                    logger.error(f"Error extracting page {page_num + 1}: {str(e)}")
                    continue
            
            result.text_content = "\n\n".join(text_parts)
            result.success = True
            
            logger.info(f"Successfully parsed {file_name} from bytes")
            
        except Exception as e:
            result.error_message = f"Error parsing PDF from bytes: {str(e)}"
            logger.error(f"{file_name}: {result.error_message}")
        
        return result


def create_parser(
    max_file_size_mb: float = 10.0,
    max_batch_size: int = 10,
    max_total_batch_size_mb: float = 50.0,
    max_pages_per_pdf: int = 100
) -> PDFParser:
    """
    Factory function to create a PDFParser with custom configuration
    
    Args:
        max_file_size_mb: Maximum size per PDF in MB
        max_batch_size: Maximum number of PDFs per batch
        max_total_batch_size_mb: Maximum total batch size in MB
        max_pages_per_pdf: Maximum pages to parse per PDF
        
    Returns:
        Configured PDFParser instance
    """
    config = PDFConfig(
        max_file_size_mb=max_file_size_mb,
        max_batch_size=max_batch_size,
        max_total_batch_size_mb=max_total_batch_size_mb,
        max_pages_per_pdf=max_pages_per_pdf
    )
    return PDFParser(config)
