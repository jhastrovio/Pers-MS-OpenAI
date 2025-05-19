"""
Attachment processor for handling email attachments.
"""

from typing import Dict, Any
import logging
from core.processing_1_2_0.engine.base import BaseProcessor
from core.graph_1_1_0.metadata import EmailDocumentMetadata
from core.processing_1_2_0.processors.document_processor import DocumentProcessor
from core.utils.logging import get_logger
from core.utils.config import PROCESSING_CONFIG
import os
import json

logger = get_logger(__name__)

class AttachmentProcessor(BaseProcessor):
    """Handles processing of email attachments using DocumentProcessor.
    
    Note: Attachments are stored in the attachment_1 folder in OneDrive,
    and their URLs are tracked just like documents in documents_1.
    """
    
    def __init__(self, doc_processor: DocumentProcessor):
        """Initialize the attachment processor.
        
        Args:
            doc_processor: DocumentProcessor instance to use for processing
        """
        self.doc_processor = doc_processor
        self.attachments_folder = PROCESSING_CONFIG["FOLDERS"]["ATTACHMENTS"]
        logger.info("AttachmentProcessor initialized with DocumentProcessor")
    
    async def process(
        self,
        *,
        file_path: str | None = None,
        content: bytes | None = None,
        filename: str | None = None,
    ) -> dict:
        """Process an email attachment, blending its own metadata with paired JSON metadata.
        
        Args:
            file_path: Optional path to the attachment file
            content: Optional raw content of the attachment
            filename: Required if content is provided, name of the attachment
            
        Returns:
            Processed attachment with blended metadata
            
        Raises:
            ProcessingError: If processing fails
        """
        # Validate input
        if not file_path and not (content and filename):
            raise ValueError("Either file_path or both content and filename must be provided")
        
        # Prepare data for document processor
        data = (
            {"file_path": file_path}
            if file_path
            else {"content": content, "filename": filename}
        )

        # Construct the OneDrive path for the attachment
        onedrive_path = f"{self.attachments_folder}/{filename}"

        # Process the attachment to get its own metadata
        result = await self.doc_processor._process_impl(
            {
                **data,
                "onedrive_path": onedrive_path,
                # meta_overrides will be handled after blending
            }
        )

        # Load paired JSON metadata if available
        if file_path:
            base_path = file_path
        elif filename:
            base_path = os.path.join(self.attachments_folder, filename)
        else:
            raise ValueError("Cannot determine filename for attachment metadata lookup.")
        json_path = base_path + ".json"
        json_fields = {}
        if os.path.exists(json_path):
            with open(json_path, "r", encoding="utf-8") as f:
                json_fields = json.load(f)
        else:
            raise ValueError(f"Paired metadata JSON file not found: {json_path}")

        # Blend/merge metadata: only specified email fields from JSON
        EMAIL_FIELDS = {
            "parent_email_id", "parent_document_id", "message_id", "subject", "to", "cc", "date", "title", "author"
        }
        meta = result.get('metadata', {})
        if hasattr(meta, 'to_dict'):
            doc_meta = meta.to_dict()
        else:
            doc_meta = dict(meta)
        blended_meta = doc_meta.copy()
        for k in EMAIL_FIELDS:
            if k in json_fields:
                blended_meta[k] = json_fields[k]
        # Ensure required attachment fields are set
        blended_meta['type'] = 'attachment'
        blended_meta['is_attachment'] = True
        blended_meta['onedrive_path'] = onedrive_path
        if 'filename' not in blended_meta and filename:
            blended_meta['filename'] = filename

        # Return the result with blended metadata
        result['metadata'] = blended_meta
        return result
        
    async def _process_impl(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Implementation of attachment processing logic.
        
        Args:
            data: Dictionary containing either:
                - file_path: Path to the file to process, or
                - content: Raw content bytes
                - filename: Name of the file (required if content is provided)
                - meta_overrides: Optional metadata overrides
                
        Returns:
            dict: Processing results including metadata and content
        """
        # This is just a wrapper around process() to satisfy the abstract method
        # The actual processing is done in process() using DocumentProcessor
        return await self.process(
            file_path=data.get('file_path'),
            content=data.get('content'),
            filename=data.get('filename')
        ) 