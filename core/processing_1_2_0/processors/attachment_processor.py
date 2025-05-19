"""
Attachment processor for handling email attachments.
"""

from typing import Dict, Any
import logging
import os
import json
from core.processing_1_2_0.engine.base import BaseProcessor, ProcessingError, ValidationError
from core.processing_1_2_0.engine.text_extractor import TextExtractor
from core.graph_1_1_0.metadata_extractor import MetadataExtractor
from core.utils.config import PROCESSING_CONFIG, CONTENT_TYPES, MAX_ATTACHMENT_SIZE, config
from core.utils.logging import get_logger
from core.graph_1_1_0.metadata import EmailDocumentMetadata

logger = get_logger(__name__)

class AttachmentProcessor(BaseProcessor):
    """Handles processing of email attachments."""
    
    def __init__(self, processor_config: dict = None):
        """Initialize the attachment processor.
        
        Args:
            processor_config: Configuration dictionary containing processing settings
        """
        self.config = processor_config or PROCESSING_CONFIG
        self.attachments_folder = config["onedrive"]["attachments_folder"]
        logger.info(f"AttachmentProcessor initialized with attachments folder: {self.attachments_folder}")
    
    def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process an email attachment.
        
        Args:
            data: Attachment data with content
            
        Returns:
            Processed attachment with extracted text and metadata
            
        Raises:
            ProcessingError: If processing fails
        """
        # Validate input
        self._validate_input(data)
        
        # Process the attachment
        return self._process_impl(data)
    
    def _process_impl(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process an email attachment.
        
        Args:
            data: Attachment data with content
            
        Returns:
            Processed attachment with extracted text and metadata
            
        Raises:
            ProcessingError: If processing fails
        """
        try:
            content = data.get('content', b'')
            filename = data.get('filename', '')
            content_type = data.get('content_type', '')
            parent_email_id = data.get('parent_email_id')
            
            # Construct the companion JSON filename (same name + .json)
            companion_json_path = os.path.join(self.attachments_folder, f"{filename}.json")
            existing_metadata = {}
            
            # Check if companion JSON exists and load it
            if os.path.exists(companion_json_path):
                try:
                    with open(companion_json_path, 'r', encoding='utf-8') as f:
                        existing_metadata = json.load(f)
                        logger.info(f"Loaded companion metadata for {filename}")
                except Exception as e:
                    logger.warning(f"Could not load companion metadata for {filename}: {str(e)}")
            
            # Extract text content (even if we have existing metadata, we might want to update it)
            text_content = TextExtractor.extract_text(content, content_type)
            if text_content.startswith('Error'):
                logger.warning(f"Text extraction warning: {text_content}")
            
            # Extract additional metadata from the file itself
            file_metadata = MetadataExtractor.extract_metadata(content, content_type)
            
            # Use existing metadata as base if available, otherwise create minimal metadata
            if existing_metadata:
                # Update existing metadata with freshly extracted file metadata
                existing_metadata.update(file_metadata)
                # Update text content if it wasn't available before or was incomplete
                if not existing_metadata.get('text_content') or len(existing_metadata.get('text_content', '')) < len(text_content):
                    existing_metadata['text_content'] = text_content
                
                # Create metadata object from existing data
                attachment_metadata = EmailDocumentMetadata(**existing_metadata)
            else:
                # No existing metadata, create minimal set with extracted data
                logger.info(f"No companion metadata found for {filename}, creating new metadata")
                import uuid
                from datetime import datetime
                
                # Create minimal metadata
                metadata = {
                    'document_id': str(uuid.uuid4()),
                    'type': 'attachment',
                    'filename': filename,
                    'one_drive_url': '',
                    'created_at': datetime.now().isoformat(),
                    'size': len(content),
                    'content_type': content_type,
                    'source': 'email',
                    'is_attachment': True,
                    'parent_email_id': parent_email_id,
                    'text_content': text_content,
                    'tags': []
                }
                
                # Add extracted file metadata
                metadata.update(file_metadata)
                
                # Create metadata object
                attachment_metadata = EmailDocumentMetadata(**metadata)
            
            # Save attachment to the dedicated attachments folder if needed
            file_path = os.path.join(self.attachments_folder, filename)
            
            logger.info(f"Successfully processed attachment: {filename}")
            return {
                'filename': filename,
                'file_path': file_path,
                'content': content,
                'metadata': attachment_metadata
            }
        except Exception as e:
            logger.error(f"Error processing attachment {data.get('filename', 'unknown')}: {str(e)}")
            raise ProcessingError(f"Failed to process attachment: {str(e)}")
    
    def _validate_input(self, data: Dict[str, Any]) -> None:
        """Validate attachment input data.
        
        Args:
            data: Input data to validate
            
        Raises:
            ValidationError: If validation fails
        """
        # Call base class validation
        super()._validate_input(data)
        
        # Additional attachment-specific validation
        content_type = data.get('content_type', '').lower()
        if content_type not in CONTENT_TYPES:
            raise ValidationError(f"Unsupported content type: {content_type}")
        
        # Validate attachment size
        content_size = len(data.get('content', b''))
        if content_size > MAX_ATTACHMENT_SIZE:
            raise ValidationError(f"Attachment size exceeds maximum limit of {MAX_ATTACHMENT_SIZE} bytes")
        
        # Validate parent email ID - relaxed requirement as we might have companion JSON
        if not data.get('parent_email_id'):
            logger.warning("Parent email ID not provided, will attempt to use companion JSON if available")
        
        # Validate content is not empty
        if not data.get('content'):
            raise ValidationError("Attachment content is empty") 