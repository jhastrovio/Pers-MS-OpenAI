"""
Document processor for handling document files.

This module provides functionality to process document files,
extract their content and metadata, and store processed results
in OneDrive via Microsoft Graph API.
"""

from typing import Dict, Any, Union
import logging
import os
import json
import tempfile
from datetime import datetime
import uuid

from core.processing_1_2_0.engine.base import BaseProcessor, ProcessingError, ValidationError
from core.processing_1_2_0.engine.text_extractor import TextExtractor
from core.graph_1_1_0.metadata_extractor import MetadataExtractor
from core.graph_1_1_0.metadata import EmailDocumentMetadata
from core.graph_1_1_0.main import GraphClient, DateTimeEncoder
from core.utils.config import PROCESSING_CONFIG
from core.utils.logging import get_logger

logger = get_logger(__name__)

class DocumentProcessor(BaseProcessor):
    """Handles processing of document files."""
    
    def __init__(self, processor_config: Dict[str, Any] = None):
        """Initialize the document processor.
        
        Args:
            processor_config: Processing configuration
        """
        self.config = processor_config or PROCESSING_CONFIG
        self.graph_client = GraphClient()
        # Initialize paths from config
        self.processed_folder = self.config["FOLDERS"]["PROCESSED_DOCUMENTS"]
        self.documents_folder = self.config["FOLDERS"]["DOCUMENTS"]
    
    async def process(self, file_path_or_data: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Process a document file or raw content.
        
        Args:
            file_path_or_data: Either a file path (str) or a dictionary containing:
                - file_path: Path to the file to process, or
                - content: Raw content bytes
                - filename: Name of the file (required if content is provided)
                - content_type: MIME type of the content (optional)
            
        Returns:
            dict: Processing results including metadata and content
        """
        try:
            # Convert file path to data dict if needed
            if isinstance(file_path_or_data, str):
                data = {"file_path": file_path_or_data}
            else:
                data = file_path_or_data
            
            # Process the document
            result = await self._process_impl(data)
            return result
            
        except ValidationError as e:
            # Propagate ValidationError directly
            raise
        except Exception as e:
            error_msg = f"Failed to process document: {str(e)}"
            logger.error(error_msg)
            raise ProcessingError(error_msg)
    
    async def _process_impl(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Implementation of document processing logic.
        
        Args:
            data: Dictionary containing either:
                - file_path: Path to the file to process, or
                - content: Raw content bytes
                - filename: Name of the file (required if content is provided)
                - content_type: MIME type of the content (optional)
                - onedrive_path: Path to the original file in OneDrive (optional)
            
        Returns:
            dict: Processing results including metadata and content
        """
        try:
            file_path = data.get('file_path')
            content = data.get('content')
            filename = data.get('filename')
            content_type = data.get('content_type')
            onedrive_path = data.get('onedrive_path')
            
            # Handle raw content
            if content is not None:
                if not filename:
                    raise ValidationError("filename is required when providing raw content")
                
                # Create temporary file
                with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as tmp_file:
                    tmp_file.write(content)
                    file_path = tmp_file.name
                
                try:
                    return await self._process_document(file_path, content_type=content_type, onedrive_path=onedrive_path)
                finally:
                    os.remove(file_path)
            
            # Handle file path
            elif file_path:
                return await self._process_document(file_path, content_type=content_type, onedrive_path=onedrive_path)
            
            else:
                raise ValidationError("Either file_path or content must be provided")
                
        except ValidationError as e:
            # Propagate ValidationError directly
            raise
        except Exception as e:
            error_msg = f"Failed to process document: {str(e)}"
            logger.error(error_msg)
            raise ProcessingError(error_msg)
    
    async def _process_document(
            self,
            file_path: str,
            *,
            content_type: str | None = None,
            meta_overrides: dict[str, Any] | None = None,
            onedrive_path: str | None = None,  # Add parameter for original OneDrive path
        ) -> Dict[str, Any]:
        """Process a document file.
        
        Args:
            file_path: Path to the document file
            content_type: Optional content type override
            meta_overrides: Optional dictionary of metadata field overrides
            onedrive_path: Optional path to the original file in OneDrive
            
        Returns:
            Processing result
        """
        try:
            # Get original filename by removing 'temp_' prefix if present
            original_filename = os.path.basename(file_path)
            if original_filename.startswith('temp_'):
                original_filename = original_filename[5:]  # Remove 'temp_' prefix
                
            logger.info(f"Processing document: {original_filename}")
            
            # Get file attributes
            file_size = os.path.getsize(file_path)
            content_type = content_type or self._detect_content_type(original_filename)
            
            # Extract text content
            text_content = await self._extract_document_text(file_path)
            
            # Extract additional metadata
            additional_metadata = {}
            try:
                with open(file_path, 'rb') as f:
                    file_content = f.read()
                    additional_metadata = MetadataExtractor.extract_metadata(file_content, content_type)
            except Exception as e:
                logger.warning(f"Error extracting additional metadata: {str(e)}")
            
            # Generate document ID
            document_id = str(uuid.uuid4())
            
            # Get the original document's OneDrive URL using the OneDrive path if provided
            original_doc_url = ""
            if onedrive_path:
                original_doc_url = await self._get_file_web_url(onedrive_path)
            else:
                logger.warning(f"No OneDrive path provided for {original_filename}, URL will be blank")
            
            # Determine type from file extension (without dot)
            file_ext = os.path.splitext(original_filename)[1].lower().lstrip('.')
            # Set date from last_modified if available
            doc_date = additional_metadata.get('last_modified', None)
            # Create document metadata using EmailDocumentMetadata
            document_metadata = EmailDocumentMetadata(
                document_id=document_id,
                type=file_ext or "document",
                filename=original_filename,
                source_url=original_doc_url,
                is_attachment=False,
                parent_email_id=None,
                message_id=None,
                subject=None,
                from_=None,
                recipients=[],
                date=doc_date,
                title=additional_metadata.get('title', os.path.splitext(original_filename)[0]),
                author=additional_metadata.get('author', ''),
                attachments=[],
                tags=[],
                text_content=text_content
            )
            
            # Save metadata to OneDrive
            try:
                # Create a new filename for the JSON metadata
                timestamp_prefix = datetime.now().strftime("%Y-%m-%d")
                base_name = os.path.splitext(original_filename)[0]
                new_filename = f"{timestamp_prefix}_{base_name}_{document_id}.json"
                
                # Convert metadata to JSON
                json_content = json.dumps(document_metadata.__dict__, indent=2, cls=DateTimeEncoder)
                
                # Upload to OneDrive
                user_email = self.config["user"]["email"]
                upload_path = f"{self.processed_folder}/{new_filename}"
                
                try:
                    # Upload JSON metadata
                    await self.graph_client.upload_file(
                        user_email,
                        upload_path,
                        json_content.encode('utf-8')
                    )
                    logger.info(f"Successfully uploaded metadata to OneDrive: {upload_path}")
                        
                except Exception as e:
                    logger.error(f"Error saving metadata to OneDrive: {str(e)}")
                    raise ProcessingError(f"Failed to save metadata to OneDrive: {str(e)}")
                
            except Exception as e:
                logger.error(f"Error saving metadata to OneDrive: {str(e)}")
                raise ProcessingError(f"Failed to save metadata to OneDrive: {str(e)}")
                
            # Return the processing result
            return {
                "filename": new_filename,
                "metadata": document_metadata,
                "content": text_content,
                "file_path": file_path
            }
                
        except Exception as e:
            error_msg = f"Failed to process document: {str(e)}"
            logger.error(f"Error processing document {file_path}: {error_msg}")
            raise ProcessingError(error_msg)
    
    async def _extract_document_text(self, file_path: str) -> str:
        """Extract text content from a document.
        
        Args:
            file_path: Path to the document
            
        Returns:
            Extracted text content
        """
        try:
            # Get the content type
            content_type = self._detect_content_type(os.path.basename(file_path))
            
            # Read the file content
            with open(file_path, 'rb') as f:
                file_content = f.read()
            
            # Extract text using TextExtractor
            text_content = TextExtractor.extract_text(file_content, content_type)
            
            # Handle extraction errors
            if text_content.startswith('Error'):
                logger.warning(f"Text extraction warning: {text_content}")
                return ""
            
            # Clean the text content
            cleaned_text = self._clean_text_content(text_content)
            return cleaned_text
        except Exception as e:
            logger.error(f"Error extracting text from {file_path}: {str(e)}")
            return ""
    
    def _detect_content_type(self, filename: str) -> str:
        """Detect content type from filename.
        
        Args:
            filename: Name of the file
            
        Returns:
            Detected content type
        """
        ext = os.path.splitext(filename)[1].lower()
        content_types = self.config["CONTENT_TYPES"]
        
        # Map file extensions to content types
        content_type_map = {
            '.pdf': 'application/pdf',
            '.doc': 'application/msword',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.txt': 'text/plain',
            '.html': 'text/html',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            '.xls': 'application/vnd.ms-excel',
            '.csv': 'text/csv',
            '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            '.ppt': 'application/vnd.ms-powerpoint'
        }
        
        return content_type_map.get(ext, 'application/octet-stream')
    
    def _clean_text_content(self, text: str) -> str:
        """Clean text content by removing headers, footers, and irrelevant content.
        
        Args:
            text: Raw text content
            
        Returns:
            Cleaned text content
        """
        if not text:
            return ""
            
        # Apply text cleaning rules from config
        text_cleaning = self.config.get("TEXT_CLEANING", {})
        
        # Remove extra whitespace
        if text_cleaning.get("REMOVE_EXTRA_WHITESPACE", True):
            import re
            text = re.sub(r'\s+', ' ', text)
        
        # Normalize line endings
        if text_cleaning.get("NORMALIZE_LINE_ENDINGS", True):
            text = text.replace("\r\n", "\n").replace("\r", "\n")
        
        # Remove control characters
        if text_cleaning.get("REMOVE_CONTROL_CHARS", True):
            import unicodedata
            text = ''.join(ch for ch in text if ch == '\n' or ch == '\t' or not unicodedata.category(ch).startswith('C'))
        
        return text.strip()
    
    async def _get_file_web_url(self, file_path: str) -> str:
        """Get the web URL of a file in OneDrive.
        
        Args:
            file_path: Full path to the file
            
        Returns:
            Web URL of the file or empty string if not found
        """
        try:
            user_email = self.config["user"]["email"]
            
            # Get the file metadata from OneDrive
            access_token = await self.graph_client._get_access_token()
            headers = {"Authorization": f"Bearer {access_token}"}
            
            # Normalize file path for OneDrive API
            file_path = file_path.replace('\\', '/').strip('/')
            url = f"https://graph.microsoft.com/v1.0/users/{user_email}/drive/root:/{file_path}"
            
            response = await self.graph_client.client.get(url, headers=headers)
            response.raise_for_status()
            
            # Get the web URL from the response
            file_data = response.json()
            web_url = file_data.get("webUrl")
            if not web_url:
                logger.error(f"No webUrl in response for {file_path}: {file_data}")
                return ""
                
            logger.info(f"Got web URL for {file_path}: {web_url}")
            return web_url
            
        except Exception as e:
            logger.error(f"Error getting web URL for {file_path}: {str(e)}")
            return "" 