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
    
    async def process(self, file_path: str, user_email: str = None) -> Dict[str, Any]:
        """Process a document file.
        
        Args:
            file_path: The path of the file to process
            user_email: Optional email address of the user. If not provided, uses config value.
            
        Returns:
            dict: Processing results including metadata and content
        """
        try:
            # Override user email in config if provided
            original_email = None
            if user_email:
                original_email = self.config["user"]["email"]
                self.config["user"]["email"] = user_email
            
            # Process the document
            result = await self._process_document(file_path)
            
            # Restore original user email if it was overridden
            if original_email:
                self.config["user"]["email"] = original_email
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing document {os.path.basename(file_path)}: {str(e)}")
            raise ProcessingError(f"Failed to process document: {str(e)}")
    
    async def _process_document(self, file_path: str) -> Dict[str, Any]:
        """Process a document file.
        
        Args:
            file_path: Path to the document file
            
        Returns:
            Processing result
        """
        try:
            logger.info(f"Processing document: {os.path.basename(file_path)}")
            
            # Get file attributes
            file_size = os.path.getsize(file_path)
            filename = os.path.basename(file_path)
            content_type = self._detect_content_type(filename)
            
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
            
            # Get web URL (if file already exists in OneDrive)
            web_url = await self._get_file_web_url(filename)
            
            # Create document metadata
            document_metadata = {
                "document_id": document_id,
                "type": "document",
                "filename": filename,
                "one_drive_url": web_url,
                "created_at": datetime.now().isoformat(),
                "size": file_size,
                "content_type": content_type,
                "source": "onedrive",
                "is_attachment": False,
                "text_content": text_content
            }
            
            # Add additional metadata
            document_metadata.update(additional_metadata)
            
            # Save metadata to OneDrive
            try:
                # Create a new filename for the JSON metadata
                timestamp_prefix = datetime.now().strftime("%Y-%m-%d")
                base_name = os.path.splitext(filename)[0]
                new_filename = f"{timestamp_prefix}_{base_name}_{document_id}.json"
                
                # Convert metadata to JSON
                json_content = json.dumps(document_metadata, indent=2, cls=DateTimeEncoder)
                
                # Upload to OneDrive
                user_email = self.config["user"]["email"]
                upload_path = f"{self.processed_folder}/{new_filename}"
                
                upload_url = await self.graph_client.upload_file(
                    user_email,
                    upload_path,
                    json_content.encode('utf-8')
                )
                
                # Update one_drive_url in metadata if upload was successful
                if upload_url:
                    document_metadata["one_drive_url"] = upload_url
                    
            except Exception as e:
                logger.error(f"Error saving metadata to OneDrive: {str(e)}")
                
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
    
    async def _get_file_web_url(self, filename: str) -> str:
        """Get the web URL of a file in OneDrive.
        
        Args:
            filename: Name of the file
            
        Returns:
            Web URL of the file or empty string if not found
        """
        try:
            user_email = self.config["user"]["email"]
            file_path = f"{self.documents_folder}/{filename}"
            
            # Check if file exists
            if await self.graph_client.file_exists(file_path):
                # Construct the URL
                # In a real implementation, you would get this from Graph API
                sharepoint_domain = "tassehcapital-my.sharepoint.com"  # Get from config if available
                user_email_domain = user_email.split('@')[1]
                user_name = user_email.split('@')[0]
                return f"https://{sharepoint_domain}/personal/{user_name}_{user_email_domain}/Documents/{file_path}"
            
            return ""
            
        except Exception as e:
            logger.warning(f"Error getting webUrl for file {filename}: {str(e)}")
            return "" 