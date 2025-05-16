"""
Base processor class that defines common functionality for all processors.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime
import uuid
import os
import logging
from time import time
from core.utils.config import config

logger = logging.getLogger(__name__)

class ProcessingError(Exception):
    """Base exception for processing errors."""
    pass

class ValidationError(ProcessingError):
    """Raised when input validation fails."""
    pass

class BaseProcessor(ABC):
    """Base class for all processors."""
    
    def __init__(self, processing_config: Dict[str, Any]):
        """Initialize the processor.
        
        Args:
            processing_config: Processing configuration
        """
        self.config = processing_config
        self.max_file_size = processing_config.get('MAX_FILE_SIZE', config['processing']['MAX_FILE_SIZE'])
        self.max_attachment_size = processing_config.get('MAX_ATTACHMENT_SIZE', config['processing']['MAX_ATTACHMENT_SIZE'])
        self.allowed_extensions = processing_config.get('ALLOWED_EXTENSIONS', config['processing']['ALLOWED_EXTENSIONS'])
        self.content_types = processing_config.get('CONTENT_TYPES', config['processing']['CONTENT_TYPES'])
        self.metadata = {}
        self._validate_config()
        logger.info(f"{self.__class__.__name__} initialized with config: {self.config}")
    
    def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process the input data with performance monitoring.
        
        Args:
            data: Input data to process
            
        Returns:
            Processed data with extracted text and metadata
            
        Raises:
            ValidationError: If input validation fails
            ProcessingError: If processing fails
        """
        start_time = time()
        try:
            self._validate_input(data)
            result = self._process_impl(data)
            processing_time = time() - start_time
            logger.info(f"Processing completed in {processing_time:.2f}s")
            return result
        except Exception as e:
            processing_time = time() - start_time
            logger.error(f"Processing failed after {processing_time:.2f}s: {str(e)}")
            raise
    
    @abstractmethod
    def _process_impl(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Implementation of the processing logic.
        
        Args:
            data: Input data to process
            
        Returns:
            Processed data with extracted text and metadata
        """
        pass
    
    def _validate_config(self) -> None:
        """Validate the processor configuration.
        
        Raises:
            ValidationError: If configuration is invalid
        """
        required_config = {'MAX_FILE_SIZE', 'ALLOWED_EXTENSIONS'}
        missing_config = required_config - set(self.config.keys())
        if missing_config:
            raise ValidationError(f"Missing required configuration: {missing_config}")
    
    def _validate_input(self, data: Dict[str, Any]) -> None:
        """Validate input data.
        
        Args:
            data: Input data to validate
            
        Raises:
            ValidationError: If validation fails
        """
        required_fields = {'content', 'filename', 'content_type'}
        missing_fields = required_fields - set(data.keys())
        if missing_fields:
            raise ValidationError(f"Missing required fields: {missing_fields}")
        
        if len(data['content']) > self.max_file_size:
            raise ValidationError(f"File size exceeds maximum limit of {self.max_file_size} bytes")
        
        ext = os.path.splitext(data['filename'])[1].lower()
        if ext not in self.allowed_extensions:
            raise ValidationError(f"Unsupported file extension: {ext}")
    
    def _generate_metadata(self, 
                          content_type: str,
                          filename: str,
                          size: int,
                          source: str,
                          parent_id: Optional[str] = None) -> Dict[str, Any]:
        """Generate base metadata for any processed item.
        
        Args:
            content_type: MIME type of the content
            filename: Name of the file
            size: Size of the content in bytes
            source: Source of the content (e.g., 'email', 'onedrive')
            parent_id: ID of the parent item if applicable
            
        Returns:
            Dictionary containing base metadata
        """
        try:
            return {
                'document_id': str(uuid.uuid4()),
                'type': 'document',
                'filename': filename,
                'one_drive_url': '',  # To be filled after upload
                'created_at': datetime.now().isoformat(),
                'size': size,
                'content_type': content_type,
                'source': source,
                'is_attachment': bool(parent_id),
                'parent_id': parent_id,
                'tags': []
            }
        except Exception as e:
            logger.error(f"Error generating metadata: {str(e)}")
            raise ProcessingError(f"Failed to generate metadata: {str(e)}")
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text content.
        
        Args:
            text: Raw text content
            
        Returns:
            Cleaned text content
        """
        if not text:
            return ""
        
        try:
            # Apply text cleaning based on configuration
            if self.config['TEXT_CLEANING']['REMOVE_EXTRA_WHITESPACE']:
                text = ' '.join(text.split())
            
            if self.config['TEXT_CLEANING']['NORMALIZE_LINE_ENDINGS']:
                text = text.replace('\r\n', '\n').replace('\r', '\n')
            
            if self.config['TEXT_CLEANING']['REMOVE_CONTROL_CHARS']:
                text = ''.join(char for char in text if char.isprintable() or char.isspace())
            
            return text.strip()
        except Exception as e:
            logger.error(f"Error cleaning text: {str(e)}")
            return text.strip()  # Return original text if cleaning fails 