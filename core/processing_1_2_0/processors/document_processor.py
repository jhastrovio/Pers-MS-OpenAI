"""
Document processor for handling document files.
"""

from typing import Dict, Any, Union
import logging
from datetime import datetime
import uuid
import os
import json
import dataclasses
from core.processing_1_2_0.engine.base import BaseProcessor, ProcessingError, ValidationError
from core.processing_1_2_0.engine.text_extractor import TextExtractor
from core.processing_1_2_0.engine.metadata_extractor import MetadataExtractor
from core.processing_1_2_0.metadata import EmailDocumentMetadata
from core.utils.config import config
from core.graph_1_1_0.main import GraphClient

logger = logging.getLogger(__name__)

class DocumentProcessor(BaseProcessor):
    """Handles processing of document files."""
    
    def __init__(self, processing_config: Dict[str, Any]):
        """Initialize the document processor.
        
        Args:
            processing_config: Processing configuration
        """
        super().__init__(processing_config)
        self.graph_client = GraphClient()
        self.processed_folder = config["onedrive"]["processed_documents_folder"]
    
    async def _upload_to_onedrive(self, filename: str, content: bytes) -> str:
        """Upload a file to OneDrive.
        
        Args:
            filename: Name of the file to upload
            content: File content in bytes
            
        Returns:
            OneDrive URL of the uploaded file
            
        Raises:
            ProcessingError: If upload fails
        """
        try:
            user_email = os.getenv("USER_EMAIL")
            if not user_email:
                raise ProcessingError("USER_EMAIL environment variable not set")
            
            # Get access token
            access_token = await self.graph_client._get_access_token()
            headers = {"Authorization": f"Bearer {access_token}"}
            
            # Upload file
            upload_url = f"https://graph.microsoft.com/v1.0/users/{user_email}/drive/root:/{self.processed_folder}/{filename}:/content"
            response = await self.graph_client.client.put(
                upload_url,
                headers=headers,
                content=content
            )
            response.raise_for_status()
            
            # Get webUrl from the upload response
            file_metadata = response.json()
            logger.debug(f"OneDrive file metadata response: {file_metadata}")
            web_url = file_metadata.get("webUrl")
            if not web_url:
                raise ProcessingError("Failed to get web URL from OneDrive response")
            
            return web_url
            
        except Exception as e:
            logger.error(f"Error uploading to OneDrive: {str(e)}")
            raise ProcessingError(f"Failed to upload to OneDrive: {str(e)}")
    
    async def process(self, data: Union[Dict[str, Any], bytes]) -> Dict[str, Any]:
        """Process a document and save to OneDrive as JSON.
        
        Args:
            data: Document data or raw bytes
            
        Returns:
            Processed document with cleaned content and metadata
            
        Raises:
            ProcessingError: If processing fails
        """
        try:
            # Process the document
            result = await self._process_impl(data)
            
            # Clean the text content
            cleaned_text = self._clean_text_content(result['metadata'].text_content)
            result['metadata'].text_content = cleaned_text
            
            # Serialize result to JSON
            json_bytes = json.dumps({
                'filename': result['filename'],
                'metadata': dataclasses.asdict(result['metadata'])
            }, ensure_ascii=False, indent=2).encode('utf-8')
            
            # Use .json extension for the filename
            base_filename = os.path.splitext(result['filename'])[0]
            json_filename = f"{base_filename}.json"
            
            # Upload the JSON file
            one_drive_url = await self._upload_to_onedrive(json_filename, json_bytes)
            result['metadata'].one_drive_url = one_drive_url
            
            return result
            
        except Exception as e:
            logger.error(f"Error saving to OneDrive: {str(e)}")
            raise ProcessingError(f"Failed to save to OneDrive: {str(e)}")
    
    def _clean_text_content(self, text: str) -> str:
        """Clean text content by removing headers, footers, repeated lines, and boilerplate/cookie/privacy policy blocks.
        
        Args:
            text: Raw text content
            
        Returns:
            Cleaned text content
        """
        if not text or text.startswith('Error'):
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
        
        total_lines = len(lines)
        for idx, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            lower_line = line.lower()
            # Remove repeated lines (likely headers/footers)
            if line_counts[line] > 1 and len(line) < 100:
                continue
            # Remove header/footer patterns
            if any(pattern in lower_line for pattern in header_footer_patterns):
                continue
            # Remove boilerplate/cookie/privacy policy patterns
            if any(pattern in lower_line for pattern in boilerplate_patterns):
                continue
            # Remove lines that are just numbers or very short
            if line.isdigit() or len(line) < 3:
                continue
            # If it's not a header/footer but contains URLs, keep it if it has other content
            if any(pattern in lower_line for pattern in url_patterns):
                words = line.split()
                if len(words) > 2:
                    cleaned_lines.append(line)
                continue
            cleaned_lines.append(line)
        # Remove trailing boilerplate blocks (if last 10 lines are mostly boilerplate, trim them)
        def is_boilerplate_block(block):
            matches = 0
            for l in block:
                l = l.lower()
                if any(pattern in l for pattern in boilerplate_patterns):
                    matches += 1
            return matches > len(block) // 2
        if len(cleaned_lines) > 10:
            last_block = cleaned_lines[-10:]
            if is_boilerplate_block(last_block):
                cleaned_lines = cleaned_lines[:-10]
        # Join lines back together
        cleaned_text = '\n'.join(cleaned_lines)
        # Remove multiple consecutive newlines
        cleaned_text = '\n'.join(line for line in cleaned_text.split('\n') if line.strip())
        return cleaned_text
    
    async def _process_impl(self, data: Union[Dict[str, Any], bytes]) -> Dict[str, Any]:
        """Process a document file.
        
        Args:
            data: Document data with content or raw bytes
            
        Returns:
            Processed document with extracted text and metadata
            
        Raises:
            ProcessingError: If processing fails
        """
        try:
            # Handle both raw bytes and dictionary input
            if isinstance(data, bytes):
                content = data
                # Generate a temporary filename for raw bytes
                temp_filename = f"document_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                content_type = self._detect_content_type(temp_filename)
                filename = temp_filename
            else:
                content = data.get('content', b'')
                filename = data.get('filename', '')
                content_type = data.get('content_type', '')
            
            # Get the webUrl of the original file
            try:
                user_email = os.getenv("USER_EMAIL")
                if not user_email:
                    raise ProcessingError("USER_EMAIL environment variable not set")
                
                # Get access token
                access_token = await self.graph_client._get_access_token()
                headers = {"Authorization": f"Bearer {access_token}"}
                
                # Get file metadata from OneDrive
                file_url = f"https://graph.microsoft.com/v1.0/users/{user_email}/drive/root:/{config['onedrive']['documents_folder']}/{filename}"
                response = await self.graph_client.client.get(file_url, headers=headers)
                response.raise_for_status()
                file_metadata = response.json()
                web_url = file_metadata.get("webUrl")
                if not web_url:
                    logger.warning(f"Could not get webUrl for original file {filename}")
                    web_url = ""
            except Exception as e:
                logger.warning(f"Error getting webUrl for original file {filename}: {str(e)}")
                web_url = ""
            
            # Extract text content
            text_content = TextExtractor.extract_text(content, content_type)
            if text_content.startswith('Error'):
                logger.warning(f"Text extraction warning: {text_content}")
                # Try to extract text with a different method if the first attempt fails
                if content_type in [config["processing"]["CONTENT_TYPES"][4], config["processing"]["CONTENT_TYPES"][5]]:  # XLSX or CSV
                    text_content = TextExtractor.extract_text(content, content_type, engine='openpyxl')
            
            # Extract additional metadata
            additional_metadata = MetadataExtractor.extract_metadata(content, content_type)
            
            # Generate base metadata
            metadata = self._generate_metadata(
                content_type=content_type,
                filename=filename,
                size=len(content) if content else 0,
                source='document'
            )
            
            # Update metadata with additional fields
            metadata.update(additional_metadata)
            
            # Set the webUrl from the original file
            metadata['one_drive_url'] = web_url
            
            # Only keep fields that are valid for EmailDocumentMetadata
            valid_fields = set(f.name for f in dataclasses.fields(EmailDocumentMetadata))
            filtered_metadata = {k: v for k, v in metadata.items() if k in valid_fields}
            
            # Create document metadata object
            document_metadata = EmailDocumentMetadata(
                **filtered_metadata,
                text_content=text_content
            )
            
            # Use .json extension for the filename, preserving original name
            base_filename = os.path.splitext(filename)[0]
            json_filename = f"{base_filename}.json"
            
            logger.info(f"Successfully processed document: {json_filename}")
            return {
                'filename': json_filename,
                'content': content,
                'metadata': document_metadata
            }
            
        except Exception as e:
            filename = data.get('filename', 'unknown') if isinstance(data, dict) else 'unknown'
            logger.error(f"Error processing document {filename}: {str(e)}")
            raise ProcessingError(f"Failed to process document: {str(e)}")
    
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
        required_fields = {'content', 'filename', 'content_type'}
        missing_fields = required_fields - set(data.keys())
        if missing_fields:
            raise ValidationError(f"Missing required fields: {missing_fields}")

        # Validate content type
        content_type = data.get('content_type', '').lower()
        if content_type not in config["processing"]["CONTENT_TYPES"].values():
            raise ValidationError(f"Unsupported content type: {content_type}")
        
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
        content_types = config["processing"]["CONTENT_TYPES"]
        
        # Map file extensions to content types
        content_type_map = {
            '.pdf': content_types[0],  # PDF
            '.doc': content_types[1],  # DOCX
            '.docx': content_types[1],  # DOCX
            '.txt': content_types[2],  # TXT
            '.text': content_types[2],  # TXT
            '.rtf': content_types[3],  # RTF
            '.xlsx': content_types[4],  # XLSX
            '.xls': content_types[4],  # XLSX
            '.csv': content_types[5],  # CSV
        }
        
        return content_type_map.get(ext, content_types[6])  # Default to UNKNOWN if not found 