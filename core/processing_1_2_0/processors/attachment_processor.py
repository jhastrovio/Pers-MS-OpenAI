"""
Attachment processor for handling email attachments.
"""

from typing import Dict, Any
import logging
from core.processing_1_2_0.engine.base import BaseProcessor, ProcessingError
from core.processing_1_2_0.engine.text_extractor import TextExtractor
from core.processing_1_2_0.engine.metadata_extractor import MetadataExtractor
from core.processing_1_2_0.metadata import EmailDocumentMetadata
from core.processing_1_2_0.constants import CONTENT_TYPES, MAX_ATTACHMENT_SIZE

logger = logging.getLogger(__name__)

class AttachmentProcessor(BaseProcessor):
    """Handles processing of email attachments."""
    
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
            
            # Extract text content
            text_content = TextExtractor.extract_text(content, content_type)
            if text_content.startswith('Error'):
                logger.warning(f"Text extraction warning: {text_content}")
            
            # Extract additional metadata
            additional_metadata = MetadataExtractor.extract_metadata(content, content_type)
            
            # Generate base metadata
            metadata = self._generate_metadata(
                content_type=content_type,
                filename=filename,
                size=len(content) if content else 0,
                source='email',
                parent_id=parent_email_id
            )
            
            # Update metadata with additional fields
            metadata.update(additional_metadata)
            
            # Create attachment metadata object
            attachment_metadata = EmailDocumentMetadata(
                **metadata,
                text_content=text_content
            )
            
            logger.info(f"Successfully processed attachment: {filename}")
            return {
                'filename': filename,
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
        if content_type not in CONTENT_TYPES.values():
            raise ValidationError(f"Unsupported content type: {content_type}")
        
        # Validate attachment size
        content_size = len(data.get('content', b''))
        if content_size > MAX_ATTACHMENT_SIZE:
            raise ValidationError(f"Attachment size exceeds maximum limit of {MAX_ATTACHMENT_SIZE} bytes")
        
        # Validate parent email ID
        if not data.get('parent_email_id'):
            raise ValidationError("Parent email ID is required for attachments")
        
        # Validate content is not empty
        if not data.get('content'):
            raise ValidationError("Attachment content is empty") 