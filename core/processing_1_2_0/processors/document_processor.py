"""
Document processor for handling document files.

This module provides functionality to process document files,
extract their content and metadata, and store processed results
in OneDrive via Microsoft Graph API.
"""

from typing import Dict, Any, Union, List, Optional
import logging
import os
import json
from datetime import datetime
import uuid
import dataclasses
from urllib.parse import quote

from core.processing_1_2_0.engine.base import BaseProcessor, ProcessingError, ValidationError
from core.processing_1_2_0.engine.text_extractor import TextExtractor
from core.graph_1_1_0.metadata_extractor import MetadataExtractor
from core.graph_1_1_0.metadata import EmailDocumentMetadata
from core.graph_1_1_0.main import GraphClient

logger = logging.getLogger(__name__)

class DocumentProcessor(BaseProcessor):
    """Handles processing of document files."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the document processor.
        
        Args:
            config: Processing configuration
        """
        super().__init__(config)
        self.graph_client = GraphClient()
        # Initialize paths from config
        self.processed_folder = self.config["onedrive"]["processed_documents_folder"]
        self.documents_folder = self.config["onedrive"]["documents_folder"]
        
    async def _process_impl(self, file_path: str) -> Dict[str, Any]:
        """Process a document.
        
        This is the implementation of the abstract method from BaseProcessor.
        
        Args:
            file_path: Path to the document file to process
            
        Returns:
            Processing result dictionary
        """
        return await self._process_document(file_path)
    
    async def _get_file_web_url(self, filename: str) -> str:
        """Get the web URL of a file in OneDrive.
        
        Args:
            filename: Name of the file
            
        Returns:
            Web URL of the file or empty string if not found
        """
        try:
            user_email = self.config["user"]["email"]
            
            # Get access token
            access_token = await self.graph_client._get_access_token()
            headers = {"Authorization": f"Bearer {access_token}"}
            
            # Get file metadata from OneDrive
            encoded_path = quote(f"{self.documents_folder}/{filename}")
            file_url = f"https://graph.microsoft.com/v1.0/users/{user_email}/drive/root:/{encoded_path}"
            
            response = await self.graph_client.client.get(file_url, headers=headers)
            response.raise_for_status()
            
            file_metadata = response.json()
            web_url = file_metadata.get("webUrl", "")
            
            return web_url
            
        except Exception as e:
            logger.warning(f"Error getting webUrl for file {filename}: {str(e)}")
            return ""
    
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
            
            # Handle extraction errors and try alternate methods if needed
            if text_content.startswith('Error'):
                logger.warning(f"Text extraction warning: {text_content}")
                
                # Try alternate extraction method for spreadsheets
                extension = os.path.splitext(file_path)[1].lower()
                if extension in ['.xlsx', '.xls', '.csv']:
                    # Read the file again to ensure fresh content
                    with open(file_path, 'rb') as f:
                        file_content = f.read()
                    text_content = TextExtractor.extract_text(file_content, content_type)
            
            # Clean the text content
            cleaned_text = self._clean_text_content(text_content)
            return cleaned_text
        except Exception as e:
            logger.error(f"Error extracting text from {file_path}: {str(e)}")
            return f"Error extracting text: {str(e)}"
    
    def _create_document_metadata(self, document_id: str, filename: str, web_url: str, 
                                  text_content: str, size: int, content_type: str = None,
                                  additional_metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create metadata for a document.
        
        Args:
            document_id: Unique identifier for the document
            filename: Name of the document file
            web_url: URL of the document in OneDrive
            text_content: Extracted text content
            size: Size of the document in bytes
            content_type: Content type of the document
            additional_metadata: Additional metadata from the document
            
        Returns:
            Document metadata
        """
        # Get the document file path and read the content if not empty
        if filename and os.path.exists(filename):
            with open(filename, 'rb') as f:
                file_content = f.read()
            
            # Get metadata from Graph API
            graph_metadata = {}
            if content_type:
                graph_metadata = MetadataExtractor.extract_metadata(file_content, content_type)
        else:
            graph_metadata = {}
        
        # Create document metadata
        metadata = {
            "document_id": document_id,
            "type": "document",
            "filename": os.path.basename(filename) if filename else None,
            "one_drive_url": web_url or "",
            "created_at": datetime.now().isoformat(),
            "size": size,
            "content_type": content_type or self._detect_content_type(filename) if filename else None,
            "source": "onedrive",
            "text_content": text_content
        }
        
        # Add fields from graph metadata if available
        if graph_metadata:
            for key, value in graph_metadata.items():
                if key not in metadata or not metadata[key]:
                    metadata[key] = value
        
        # Update with additional metadata, but only keep valid fields
        if additional_metadata:
            filtered_additional = {k: v for k, v in additional_metadata.items() if k in metadata}
            metadata.update(filtered_additional)
        
        return metadata
    
    async def _process_document(self, file_path: str) -> Dict[str, Any]:
        """Process a document file.
        
        This is the implementation of BaseProcessor._process_impl method.
        
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
            
            # Generate document ID
            document_id = self._generate_document_id(filename)
            
            # Get web URL
            web_url = await self._get_web_url(filename.replace("temp_", ""))
            
            # Create document metadata
            document_metadata = self._create_document_metadata(
                document_id=document_id,
                filename=file_path,
                web_url=web_url,
                text_content=text_content,
                size=file_size,
                content_type=content_type
            )
            
            # Save metadata to OneDrive
            try:
                # Create a new filename for the JSON metadata
                timestamp_prefix = datetime.now().strftime("%Y-%m-%d")
                base_name = os.path.splitext(filename)[0]
                new_filename = f"{timestamp_prefix}_{base_name}_{document_id}.json"
                
                # Convert metadata to JSON
                json_content = json.dumps(document_metadata, indent=2)
                
                # Upload to OneDrive
                processed_folder = self.config["onedrive"]["processed_documents_folder"]
                upload_path = f"{processed_folder}/{new_filename}"
                
                # Check if file already exists
                if await self._file_exists(upload_path):
                    logger.warning(f"Document {new_filename} already exists. Skipping upload.")
                else:
                    upload_response = await self._upload_to_onedrive(
                        filename=new_filename, 
                        content=json_content.encode('utf-8'),
                        folder=processed_folder
                    )
                    
                    # Update one_drive_url in metadata if upload was successful and url was returned
                    if upload_response:
                        document_metadata["one_drive_url"] = upload_response
            except Exception as e:
                logger.error(f"Error saving metadata to OneDrive: {str(e)}")
                
            # Return the processing result
            return {
                "filename": new_filename,
                "metadata": document_metadata,
                "content": file_path
            }
                
        except Exception as e:
            error_msg = f"Failed to process document: {str(e)}"
            logger.error(f"Error processing document {file_path}: {error_msg}")
            raise ProcessingError(error_msg)
    
    async def process(self, file_path: str, user_email: str = None) -> Dict[str, Any]:
        """Process a document file.
        
        This is the public API method.
        
        Args:
            file_path: The path of the file to process
            user_email: Optional email address of the user. If not provided, uses config value.
            
        Returns:
            dict: Processing results including metadata and content
        """
        try:
            # Override user email in config if provided
            if user_email:
                original_email = self.config["user"]["email"]
                self.config["user"]["email"] = user_email
            
            # Process the document using the implementation method directly
            # We cannot use BaseProcessor.process() because it expects a dict
            result = await self._process_impl(file_path)
            
            # Restore original user email if it was overridden
            if user_email:
                self.config["user"]["email"] = original_email
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing document {os.path.basename(file_path)}: {str(e)}")
            raise ProcessingError(f"Failed to process document: {str(e)}")
    
    async def _upload_to_onedrive(self, filename: str, content: bytes, folder: str = "") -> str:
        """Upload a file to OneDrive.
        
        Args:
            filename: Name of the file to upload
            content: File content in bytes
            folder: Folder in OneDrive to upload the file to (defaults to processed_folder)
            
        Returns:
            OneDrive URL of the uploaded file
            
        Raises:
            ProcessingError: If upload fails
        """
        try:
            user_email = self.config["user"]["email"]
            
            # Use provided folder or default to processed folder
            target_folder = folder or self.processed_folder
            
            # Get access token
            access_token = await self.graph_client._get_access_token()
            headers = {"Authorization": f"Bearer {access_token}"}
            
            # Upload file
            encoded_path = quote(f"{target_folder}/{filename}")
            upload_url = f"https://graph.microsoft.com/v1.0/users/{user_email}/drive/root:/{encoded_path}:/content"
            
            response = await self.graph_client.client.put(
                upload_url,
                headers=headers,
                content=content
            )
            response.raise_for_status()
            
            # Get webUrl from the upload response
            file_metadata = response.json()
            logger.debug(f"OneDrive file metadata response: {file_metadata}")
            web_url = file_metadata.get("webUrl", "")
            
            return web_url
            
        except Exception as e:
            logger.error(f"Error uploading to OneDrive: {str(e)}")
            raise ProcessingError(f"Failed to upload to OneDrive: {str(e)}")
    
    def _clean_text_content(self, text: str) -> str:
        """Clean text content by removing headers, footers, repeated lines, and boilerplate content.
        
        Args:
            text: Raw text content
            
        Returns:
            Cleaned text content
        """
        if not text or text.startswith('Error'):
            return text
            
        # Special case for single lines with URLs
        if len(text.split('\n')) == 1 and any(url_pattern in text.lower() for url_pattern in ['http://', 'https://', 'www.']):
            # If it's a single line with a URL and has more than 5 words, keep it as is
            words = text.split()
            if len(words) > 5:
            return text
            
        # Split into lines
        lines = text.split('\n')
        cleaned_lines = []
        line_counts = {}
        
        # Patterns that indicate header/footer content
        header_footer_patterns = [
            'page', 'confidential', 'copyright', 'all rights reserved',
            '©', '®', '™', '•', '–', '—'
        ]
        # Patterns for cookie/privacy policy/boilerplate
        boilerplate_patterns = [
            'this site uses cookies', 'privacy policy', 'cookie and privacy settings',
            'google analytics', 'external services', 'webfont', 'map settings',
            'reCaptcha', 'video embeds', 'allow them', 'how we use cookies',
            'by continuing to browse the site', 'we may request cookies',
            'you are free to opt out', 'we provide you with a list of stored cookies',
            'browser security settings', 'marketing campaigns', 'customize our website',
            'enhance your experience', 'disable tracking', 'remove all set cookies',
            'domain', 'security reasons', 'aggregate form', 'opt in', 'opt out',
            'block or delete cookies', 'prompt you to accept/refuse cookies',
            'google webfonts', 'google maps', 'google recaptcha', 'vimeo', 'youtube',
            'video providers', 'personal data', 'ip address', 'block them here',
            'be aware that this', 'following cookies are also needed', 'choose if you want to allow them'
        ]
        # URL patterns
        url_patterns = ['http://', 'https://', 'www.', '.com', '.org', '.net']
        
        # Count line occurrences (for repeated header/footer detection)
        for line in lines:
            line = line.strip()
            if not line:
                continue
            line_counts[line] = line_counts.get(line, 0) + 1
        
        # Process each line
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            lower_line = line.lower()
            
            # Skip repeated lines (likely headers/footers)
            if line_counts[line] > 1 and len(line) < 100:
                continue
                
            # Skip header/footer patterns
            if any(pattern in lower_line for pattern in header_footer_patterns):
                continue
                
            # Skip boilerplate/cookie/privacy policy patterns
            if any(pattern in lower_line for pattern in boilerplate_patterns):
                continue
                
            # Skip lines that are just numbers or very short
            if line.isdigit() or len(line) < 3:
                continue
                
            # Special handling for URLs - keep if they have other content
            if any(pattern in lower_line for pattern in url_patterns):
                words = line.split()
                if len(words) > 2:  # Has more than just a URL
                    cleaned_lines.append(line)
                continue
                
            # Keep all other lines
            cleaned_lines.append(line)
        
        # Remove trailing boilerplate blocks
        if len(cleaned_lines) > 10:
            last_block = cleaned_lines[-10:]
            if self._is_boilerplate_block(last_block, boilerplate_patterns):
                cleaned_lines = cleaned_lines[:-10]
        
        # Join lines back together and clean up multiple newlines
        cleaned_text = '\n'.join(cleaned_lines)
        cleaned_text = '\n'.join(line for line in cleaned_text.split('\n') if line.strip())
        
        return cleaned_text
    
    def _is_boilerplate_block(self, block: List[str], patterns: List[str]) -> bool:
        """Check if a block of text is mostly boilerplate.
        
        Args:
            block: List of text lines
            patterns: List of boilerplate patterns
            
        Returns:
            True if the block is mostly boilerplate, False otherwise
        """
        matches = 0
        for line in block:
            line = line.lower()
            if any(pattern in line for pattern in patterns):
                matches += 1
        return matches > len(block) // 2
    
    def _validate_input(self, data: Union[Dict[str, Any], bytes]) -> None:
        """Validate document input data.
        
        Args:
            data: Input data to validate (either dict or bytes)
            
        Raises:
            ValidationError: If validation fails
        """
        if isinstance(data, bytes):
            # For raw bytes, we only need to validate that it's not empty
            if not data:
                raise ValidationError("Empty document content")
            return

        # For dictionary input, validate required fields
        required_fields = {'content', 'filename'}
        missing_fields = required_fields - set(data.keys())
        if missing_fields:
            raise ValidationError(f"Missing required fields: {missing_fields}")
        
        # Validate content is not empty
        if not data.get('content'):
            raise ValidationError("Document content is empty")
    
    def _detect_content_type(self, filename: str) -> str:
        """Detect content type from filename.
        
        Args:
            filename: Name of the file
            
        Returns:
            Detected content type
        """
        ext = os.path.splitext(filename)[1].lower()
        content_types = self.config["processing"]["CONTENT_TYPES"]
        
        # Map file extensions to content types
        content_type_map = {
            '.pdf': content_types[0],   # PDF
            '.doc': content_types[1],   # DOCX
            '.docx': content_types[1],  # DOCX
            '.txt': content_types[2],   # TXT
            '.text': content_types[2],  # TXT
            '.rtf': content_types[3],   # RTF
            '.xlsx': content_types[4],  # XLSX
            '.xls': content_types[4],   # XLSX
            '.csv': content_types[5],   # CSV
        }
        
        return content_type_map.get(ext, content_types[6])  # Default to UNKNOWN if not found 

    def _generate_document_id(self, filename: str) -> str:
        """Generate a unique document ID.
        
        Args:
            filename: The filename to use as a base for the ID
            
        Returns:
            Unique document ID
        """
        # Use UUID for now, but could be customized based on filename
        return str(uuid.uuid4()) 

    async def _get_web_url(self, filename: str) -> str:
        """Get the web URL for a file in OneDrive.
        
        Args:
            filename: Name of the file
            
        Returns:
            OneDrive web URL
        """
        try:
            user_email = self.config["user"]["email"]
            folder_path = self.config["onedrive"]["documents_folder"]
            file_path = f"{folder_path}/{filename}"
            
            # Try to get webUrl from Graph API
            try:
                # Get file information with access token
                access_token = await self.graph_client._get_access_token()
                headers = {"Authorization": f"Bearer {access_token}"}
                
                # Construct Graph API URL to get file information
                url = f"https://graph.microsoft.com/v1.0/users/{user_email}/drive/root:/{file_path}"
                
                # Make API call
                response = await self.graph_client.client.get(url, headers=headers)
                response.raise_for_status()
                
                # Get webUrl from response
                data = response.json()
                if 'webUrl' in data:
                    return data['webUrl']
            except Exception as e:
                logger.warning(f"Error getting webUrl for file {filename}: {str(e)}")
            
            # Fallback: Construct a OneDrive URL
            sharepoint_domain = "tassehcapital-my.sharepoint.com"  # Use actual domain from config if available
            user_email_domain = user_email.split('@')[1]
            user_name = user_email.split('@')[0]
            
            # Format the URL
            onedrive_url = f"https://{sharepoint_domain}/personal/{user_name}_{user_email_domain}/Documents/{file_path}"
            return onedrive_url
        except Exception as e:
            logger.warning(f"Error getting web URL for {filename}: {str(e)}")
            return "" 

    async def _file_exists(self, file_path: str) -> bool:
        """Check if a file exists in OneDrive.
        
        Args:
            file_path: Path to the file in OneDrive
            
        Returns:
            True if the file exists, False otherwise
        """
        try:
            # Use the file_exists method from GraphClient if available
            if hasattr(self.graph_client, 'file_exists'):
                return await self.graph_client.file_exists(file_path)
            
            # Fallback: Check directly with Graph API
            user_email = self.config["user"]["email"]
            access_token = await self.graph_client._get_access_token()
            headers = {"Authorization": f"Bearer {access_token}"}
            
            # Construct Graph API URL
            url = f"https://graph.microsoft.com/v1.0/users/{user_email}/drive/root:/{file_path}"
            
            # Make API call
            response = await self.graph_client.client.get(url, headers=headers)
            
            # If we get a successful response, the file exists
            return response.status_code == 200
        except Exception as e:
            # If we get an error (likely 404), the file doesn't exist
            return False 