"""
Email processor for handling email messages.

This module provides functionality to process email messages (.eml format),
extract their content and metadata, and store processed results in OneDrive
via Microsoft Graph API.
"""

from typing import Dict, Any, List, Union
import logging
from datetime import datetime
import uuid
import email
from email import policy
from email.parser import BytesParser
from email.utils import parsedate_to_datetime
import re
from html import unescape
import os
from core.processing_1_2_0.engine.base import BaseProcessor, ProcessingError, ValidationError
from core.processing_1_2_0.engine.text_extractor import TextExtractor
from core.graph_1_1_0.metadata_extractor import MetadataExtractor
from core.graph_1_1_0.metadata import EmailDocumentMetadata
from core.utils.config import config
from core.graph_1_1_0.main import GraphClient
from core.utils.logging import get_logger
import dataclasses
from bs4 import BeautifulSoup
import json
import asyncio
from core.utils.filename_utils import create_hybrid_filename

logger = get_logger(__name__)

# Define allowed attachment types
ALLOWED_ATTACHMENT_TYPES = {
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.ms-powerpoint',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'text/plain',
    'text/html',
    'text/csv'
}

class EmailProcessor(BaseProcessor):
    """
    Processes email messages in .eml format.
    
    This processor handles parsing of email content, extraction of metadata,
    conversion of content to clean text, and storage of processed results.
    It supports handling both email bodies and attachments, and uses the
    Microsoft Graph API for OneDrive operations.
    """
    
    def __init__(self, processor_config: dict = None):
        """Initialize the email processor.
        
        Args:
            processor_config: Configuration dictionary containing processing settings
        """
        self.config = processor_config or config
        self.metadata_extractor = MetadataExtractor()
        self.text_extractor = TextExtractor()
        self.graph_client = GraphClient()
        # Initialize attachment processing if needed
        self.attachment_processor = None  # Will be initialized on demand
    
    async def process(self, eml: bytes, user_email: str = None) -> dict:
        """Process an email message from .eml bytes.
        
        Args:
            eml: Raw .eml file content (bytes)
            user_email: Optional email address of the user
        
        Returns:
            dict: Processing results including metadata
        """
        try:
            # Process the email
            return await self._process_email(eml, graph_metadata={})
        except Exception as e:
            logger.error(f"Email processing error: {str(e)}")
            raise ProcessingError(f"Failed to process email: {str(e)}")
    
    async def _process_email(self, eml_content: bytes, graph_metadata: dict) -> dict:
        """Process an email message.
        
        Args:
            eml_content: Raw EML content
            graph_metadata: Metadata from Graph API (can be empty)
        
        Returns:
            dict: Processed email data with metadata
        """
        try:
            # Parse email
            msg = BytesParser(policy=policy.default).parsebytes(eml_content)
            
            # Extract basic metadata
            message_id = msg.get('Message-ID', '').strip('<>') or str(uuid.uuid4())
            subject = msg.get('Subject', '')
            from_ = msg.get('From', '')
            to = msg.get_all('To', [])
            cc = msg.get_all('Cc', [])
            date_str = msg.get('Date', '')
            
            # Parse email addresses
            to_emails = self._parse_email_addresses(to)
            cc_emails = self._parse_email_addresses(cc)
            from_email = self._parse_email_addresses([from_])[0] if from_ else ''
            
            # Parse date
            try:
                date = parsedate_to_datetime(date_str).isoformat() if date_str else ''
            except:
                date = ''
            
            # Extract text content
            text_content = self._extract_text_content(msg)
            
            # Create a default outlook URL based on message ID if not provided in graph_metadata
            default_outlook_url = ""
            if message_id:
                # Create a standard Outlook web URL format
                user_email = self.config["user"]["email"]
                tenant = user_email.split('@')[1]
                default_outlook_url = f"https://outlook.office.com/mail/inbox/id/{message_id}"
            
            # Create email metadata
            email_metadata = EmailDocumentMetadata(
                document_id=message_id,
                type="email",
                filename=None,  # To be set after naming
                one_drive_url="",  # Will be updated after upload
                outlook_url=graph_metadata.get("webUrl", default_outlook_url),
                created_at=datetime.now().isoformat(),
                size=len(eml_content),
                content_type="message/rfc822",
                source="email",
                is_attachment=False,
                parent_email_id=None,
                message_id=message_id,
                subject=subject,
                from_=from_email,  # This is crucial - keep the underscore in from_
                to=to_emails,
                cc=cc_emails,
                date=date,
                text_content=text_content,
                attachments=[],  # To be populated by attachment processor
                tags=[]
            )
            
            # Generate a safe filename
            safe_subject = ''.join(c for c in subject if c.isalnum() or c in (' ', '_')).rstrip().replace(' ', '_')[:50]
            date_prefix = date[:10].replace(':', '-') if date else datetime.now().strftime('%Y-%m-%d')
            new_filename = f"{date_prefix}_{safe_subject}_{message_id}.json"
            email_metadata.filename = new_filename
            
            # Save email metadata and get OneDrive webUrl
            try:
                # First, try to verify the OneDrive URL isn't empty
                if not email_metadata.one_drive_url or email_metadata.one_drive_url == "":
                    # Generate a proper SharePoint URL for the file in OneDrive
                    sharepoint_domain = "tassehcapital-my.sharepoint.com"  # Get from config if available
                    user_email_domain = user_email.split('@')[1]
                    user_name = user_email.split('@')[0]
                    folder_path = self.config["onedrive"]["processed_emails_folder"]
                    onedrive_url = f"https://{sharepoint_domain}/personal/{user_name}_{user_email_domain}/Documents/{folder_path}/{new_filename}"
                    email_metadata.one_drive_url = onedrive_url
                
                json_content = email_metadata.to_json()
                
                # Use proper upload_file method instead of non-existent save_email_content_to_onedrive
                folder_path = self.config["onedrive"]["processed_emails_folder"]
                file_path = f"{folder_path}/{new_filename}"
                user_email = self.config["user"]["email"]
                upload_response = await self.graph_client.upload_file(
                    user_email,
                    file_path,
                    json_content.encode('utf-8')
                )
                
                # Generate a proper SharePoint URL for the file in OneDrive
                # The upload_response might not contain the full OneDrive URL we need
                sharepoint_domain = "tassehcapital-my.sharepoint.com"  # Get from config if available
                user_email_domain = user_email.split('@')[1]
                user_name = user_email.split('@')[0]
                onedrive_url = f"https://{sharepoint_domain}/personal/{user_name}_{user_email_domain}/Documents/{file_path}"
                
                # Set the OneDrive URL in metadata - ensure it's never blank
                if upload_response and 'https://' in upload_response:
                    email_metadata.one_drive_url = upload_response
                else:
                    email_metadata.one_drive_url = onedrive_url
                
                # Add debugging to verify the URL is set
                logger.debug(f"Set OneDrive URL to: {email_metadata.one_drive_url}")
                
                # Re-encode the JSON with the updated URL to ensure it's saved
                updated_json_content = email_metadata.to_json()
                
                # If the URL has been updated, upload the file again to ensure it contains the correct URL
                if json_content != updated_json_content:
                    await self.graph_client.upload_file(
                        user_email,
                        file_path,
                        updated_json_content.encode('utf-8')
                    )
                
            except Exception as e:
                logger.error(f"Error saving email metadata: {str(e)}")
                raise ProcessingError(f"Failed to save email metadata: {str(e)}")
            
            # Convert to dict for return
            # Note: EmailDocumentMetadata.to_dict() renames 'from_' to 'from'
            metadata_dict = email_metadata.to_dict()
            # But tests expect 'from_' in the result, so we need to add it back
            if 'from' in metadata_dict:
                metadata_dict['from_'] = metadata_dict['from']
            
            # Ensure one_drive_url is never null or empty in the result
            if not metadata_dict.get('one_drive_url'):
                sharepoint_domain = "tassehcapital-my.sharepoint.com"
                user_email = self.config["user"]["email"]
                user_email_domain = user_email.split('@')[1]
                user_name = user_email.split('@')[0]
                folder_path = self.config["onedrive"]["processed_emails_folder"]
                metadata_dict['one_drive_url'] = f"https://{sharepoint_domain}/personal/{user_name}_{user_email_domain}/Documents/{folder_path}/{new_filename}"
                logger.debug(f"Fixed missing OneDrive URL in final result: {metadata_dict['one_drive_url']}")
            
            return {
                "subject": subject,
                "body": text_content,
                "filename": new_filename,
                "metadata": metadata_dict
            }
            
        except Exception as e:
            logger.error(f"Error processing email: {str(e)}")
            raise ProcessingError(f"Failed to process email: {str(e)}")
    
    def _extract_text_content(self, msg: email.message.Message) -> str:
        """Extract text content from an email message.
        
        Args:
            msg: Email message object
            
        Returns:
            Extracted and cleaned text content
        """
        text_content = None
        if msg.is_multipart():
            # First try to find text/plain part
            for part in msg.walk():
                if part.get_content_type() == 'text/plain' and not part.get_filename():
                    text_content = part.get_content()
                    break
            # If no text/plain found, try text/html
            if not text_content:
                for part in msg.walk():
                    if part.get_content_type() == 'text/html' and not part.get_filename():
                        text_content = part.get_content()
                        break
        else:
            if msg.get_content_type() == 'text/plain':
                text_content = msg.get_content()
            elif msg.get_content_type() == 'text/html':
                text_content = msg.get_content()
        
        return self._clean_text(text_content) if text_content else ''
    
    def _parse_email_addresses(self, addresses: List[str]) -> List[str]:
        """Parse email addresses from a list of address strings.
        
        Args:
            addresses: List of email address strings
            
        Returns:
            List of parsed email addresses
        """
        if not addresses:
            return []
        parsed = email.utils.getaddresses(addresses)
        return [addr for name, addr in parsed if addr]
    
    def _clean_text(self, text: str) -> str:
        """Clean text content by removing HTML tags, normalizing whitespace, and replacing smart punctuation.
        
        Args:
            text: Raw text content
            
        Returns:
            Cleaned text content
        """
        if not text:
            return ""
        try:
            # Handle encoding issues
            if isinstance(text, bytes):
                text = text.decode('utf-8', errors='replace')
            elif not isinstance(text, str):
                text = str(text)

            # Remove HTML comments
            text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)
            # Remove HTML tags
            text = re.sub(r'<[^>]+>', ' ', text)
            # Convert HTML entities
            text = unescape(text)
            # Remove extra whitespace
            text = re.sub(r'\s+', ' ', text)
            # Remove any remaining HTML/CSS artifacts
            text = re.sub(r'@media.*?}', '', text, flags=re.DOTALL)
            text = re.sub(r'Begin.*?-->', '', text, flags=re.DOTALL)

            # Replace smart quotes, dashes, ellipses, etc.
            smart_map = {
                '\u2018': "'", '\u2019': "'", '\u201c': '"', '\u201d': '"',
                '\u2013': '-', '\u2014': '-', '\u2026': '...', '\u2012': '-',
                '\u2010': '-', '\u2011': '-', '\u00a0': ' ', '\u200b': '',
                '\u201b': "'", '\u2032': "'", '\u2033': '"',
            }
            for uni, repl in smart_map.items():
                text = text.replace(uni.encode('utf-8').decode('utf-8'), repl)
            # Replace any remaining problematic replacement chars
            text = text.replace('\ufffd', '')
            # Remove any remaining non-printable or non-ASCII characters
            text = ''.join(char for char in text if (char.isprintable() and ord(char) < 128) or char.isspace())
            # Normalize whitespace again
            text = re.sub(r'\s+', ' ', text)
            return text.strip()
        except Exception as e:
            logger.error(f"Error cleaning text content: {str(e)}")
            return text.strip() if text else ""
    
    async def close(self):
        """Close the Graph client."""
        await self.graph_client.close()

    async def _upload_to_onedrive(self, filename: str, content: bytes, folder: str = "") -> str:
        """Upload a file to OneDrive.
        
        Args:
            filename: Name of the file to upload
            content: File content in bytes
            folder: Folder in OneDrive to upload the file to
            
        Returns:
            OneDrive URL of the uploaded file
            
        Raises:
            ProcessingError: If upload fails
        """
        try:
            user_email = self.config["user"]["email"]
            
            # Get access token
            access_token = await self.graph_client._get_access_token()
            headers = {"Authorization": f"Bearer {access_token}"}
            
            # Upload file
            upload_url = f"https://graph.microsoft.com/v1.0/users/{user_email}/drive/root:/{folder}/{filename}:/content"
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
    
    async def _process_impl(self, data: Union[Dict[str, Any], bytes], filename: str = None) -> Dict[str, Any]:
        """Process an email message (required by BaseProcessor).
        
        Args:
            data: Email data as dictionary or raw bytes
            filename: Optional filename for the email
            
        Returns:
            Dictionary containing processed email data
        """
        try:
            # For raw EML data (bytes), use the process method
            if isinstance(data, bytes):
                return await self._process_email(data, {})
            
            # For dictionary data (from Graph API), extract metadata and content
            if isinstance(data, dict):
                # Validate input
                self._validate_input(data)
                
                # Extract content
                body = data.get('body', {})
                content_type = body.get('contentType', 'text/plain')
                content = body.get('content', '')
                
                # Create metadata
                metadata = self._extract_email_metadata(data)
                
                # Generate a safe filename if not provided
                if not filename:
                    subject = data.get('subject', '')
                    safe_subject = ''.join(c for c in subject if c.isalnum() or c in (' ', '_')).rstrip().replace(' ', '_')[:50]
                    filename = f"{datetime.now().strftime('%Y-%m-%d')}_{safe_subject}_{metadata['document_id']}.json"
                
                # Save metadata
                metadata['filename'] = filename
                await self._save_processed_document(
                    f"{self.config['onedrive']['processed_emails_folder']}/{filename}",
                    metadata
                )
                
                return {
                    "email_id": metadata['document_id'],
                    "metadata": metadata,
                    "content": content
                }
            
            raise ValidationError("Invalid input data type")
            
        except Exception as e:
            logger.error(f"Error in _process_impl: {str(e)}")
            raise ProcessingError(f"Failed to process email: {str(e)}")
    
    async def _save_processed_document(self, file_path: str, content: Union[Dict, str]) -> str:
        """Save processed document to OneDrive.
        
        Args:
            file_path: Path to save the document to
            content: Content to save (dict will be converted to JSON)
            
        Returns:
            OneDrive URL of the saved document
        """
        try:
            # Convert dict to JSON if needed
            if isinstance(content, dict):
                content_bytes = json.dumps(content, indent=2).encode('utf-8')
            elif isinstance(content, str):
                content_bytes = content.encode('utf-8')
            else:
                content_bytes = bytes(content)
                
            # Extract folder and filename
            if '/' in file_path:
                folder, filename = file_path.rsplit('/', 1)
            else:
                folder, filename = '', file_path
                
            # Upload to OneDrive
            return await self._upload_to_onedrive(filename, content_bytes, folder)
        
        except Exception as e:
            logger.error(f"Error saving processed document: {str(e)}")
            raise ProcessingError(f"Failed to save processed document: {str(e)}")
    
    def _validate_input(self, data: Union[Dict[str, Any], bytes]) -> None:
        """Validate email input data.
        
        Args:
            data: Input data to validate (either dict or bytes)
            
        Raises:
            ValidationError: If validation fails
        """
        if isinstance(data, bytes):
            # For EML files, we only need to validate that it's not empty
            if not data:
                raise ValidationError("Empty EML file")
            return

        # For Graph API data, validate required fields
        required_fields = {'subject', 'body'}
        missing_fields = required_fields - set(data.keys())
        if missing_fields:
            raise ValidationError(f"Missing required fields: {missing_fields}")

        # Validate body format
        body = data.get('body', {})
        if not isinstance(body, dict):
            raise ValidationError("Body must be a dictionary")

        # Validate content type
        content_type = body.get('contentType', 'text/plain')
        if content_type not in ['text/plain', 'text/html']:
            raise ValidationError(f"Unsupported content type: {content_type}")
    
    def _extract_email_metadata(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract email-specific metadata from Graph API data.

        Args:
            data: Email data from Graph API

        Returns:
            Dictionary of email metadata
        """
        # Extract basic fields
        subject = data.get('subject', '')
        from_ = data.get('from', {}).get('emailAddress', {}).get('address', '')
        to = [r.get('emailAddress', {}).get('address', '') for r in data.get('toRecipients', [])]
        cc = [r.get('emailAddress', {}).get('address', '') for r in data.get('ccRecipients', [])]
        date = data.get('receivedDateTime', '')
        message_id = data.get('id', str(uuid.uuid4()))

        # Extract additional fields
        importance = data.get('importance', 'normal')
        conversation_id = data.get('conversationId', '')
        categories = data.get('categories', [])
        flag_status = data.get('flag', {}).get('flagStatus', 'notFlagged')

        return {
            'document_id': message_id,
            'type': 'email',
            'one_drive_url': '',  # To be filled after upload
            'created_at': datetime.now().isoformat(),
            'source': 'email',
            'is_attachment': False,
            'parent_email_id': None,
            'message_id': message_id,
            'subject': subject,
            'from_': from_,
            'to': to,
            'cc': cc,
            'date': date,
            'attachments': [],
            'tags': categories,
            'importance': importance,
            'conversation_id': conversation_id,
            'flag_status': flag_status
        }
    
    async def _process_attachments(self, attachments: List[Dict[str, Any]], parent_id: str) -> List[Dict[str, Any]]:
        """Process email attachments.
        
        Args:
            attachments: List of attachment data
            parent_id: ID of the parent email
            
        Returns:
            List of processed attachments
        """
        # Initialize attachment processor if needed
        if self.attachment_processor is None:
            from core.processing_1_2_0.processors.attachment_processor import AttachmentProcessor
            self.attachment_processor = AttachmentProcessor(self.config)
            
        processed_attachments = []
        for attachment in attachments:
            try:
                # Add parent email ID to attachment data
                attachment['parent_email_id'] = parent_id
                
                # Process attachment using attachment processor
                processed = await self.attachment_processor.process(attachment)
                processed_attachments.append(processed)
            except Exception as e:
                logger.error(f"Error processing attachment {attachment.get('name', 'unknown')}: {str(e)}")
                continue
        
        return processed_attachments 

    async def file_exists(self, file_path: str) -> bool:
        """Check if a file exists in OneDrive.
        
        Args:
            file_path: Path to the file in OneDrive
            
        Returns:
            bool: True if the file exists, False otherwise
        """
        try:
            user_email = self.config["user"]["email"]
            access_token = await self.graph_client._get_access_token()
            headers = {"Authorization": f"Bearer {access_token}"}
            
            # Normalize the path for OneDrive API
            file_path = file_path.replace('\\', '/').strip('/')
            url = f"https://graph.microsoft.com/v1.0/users/{user_email}/drive/root:/{file_path}"
            
            response = await self.graph_client.client.get(url, headers=headers)
            response.raise_for_status()
            
            # If we get here, the file exists
            return True
            
        except Exception as e:
            logger.debug(f"File check failed for {file_path}: {str(e)}")
            return False 