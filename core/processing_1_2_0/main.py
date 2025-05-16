"""
Data Processing Module

This module handles cleaning, enrichment, and processing of data from various sources:
- Email cleaning and metadata extraction
- Document text extraction
- Attachment processing
"""

from typing import Dict, Any
import logging
from core.processing_1_2_0.processors.document_processor import DocumentProcessor
from core.processing_1_2_0.processors.attachment_processor import AttachmentProcessor
from core.processing_1_2_0.processors.email_processor import EmailProcessor
from core.processing_1_2_0.engine.base import ProcessingError
from core.processing_1_2_0.constants import PROCESSING_CONFIG

logger = logging.getLogger(__name__)

class DataProcessor:
    """Handles data processing and cleaning operations."""
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize the data processor with configurations.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or PROCESSING_CONFIG
        self.document_processor = DocumentProcessor(self.config)
        self.attachment_processor = AttachmentProcessor(self.config)
        self.email_processor = EmailProcessor(self.config)
        logger.info("DataProcessor initialized with configuration")
    
    def process_email(self, raw_email: Dict[str, Any]) -> Dict[str, Any]:
        """Process and clean an email message.
        
        Args:
            raw_email: Raw email data from Graph API
            
        Returns:
            Cleaned and enriched email data
            
        Raises:
            ProcessingError: If processing fails
        """
        try:
            return self.email_processor.process(raw_email)
        except Exception as e:
            logger.error(f"Error processing email: {str(e)}")
            raise ProcessingError(f"Failed to process email: {str(e)}")
    
    def extract_document_text(self, document: Dict[str, Any]) -> str:
        """Extract text content from a document.
        
        Args:
            document: Document data with content
            
        Returns:
            Extracted text content
            
        Raises:
            ProcessingError: If processing fails
        """
        try:
            processed = self.document_processor.process(document)
            return processed['metadata'].text_content
        except Exception as e:
            logger.error(f"Error extracting document text: {str(e)}")
            raise ProcessingError(f"Failed to extract document text: {str(e)}")
    
    def process_attachment(self, attachment: Dict[str, Any]) -> Dict[str, Any]:
        """Process an email attachment.
        
        Args:
            attachment: Attachment data with content
            
        Returns:
            Processed attachment with extracted text and metadata
            
        Raises:
            ProcessingError: If processing fails
        """
        try:
            return self.attachment_processor.process(attachment)
        except Exception as e:
            logger.error(f"Error processing attachment: {str(e)}")
            raise ProcessingError(f"Failed to process attachment: {str(e)}")
