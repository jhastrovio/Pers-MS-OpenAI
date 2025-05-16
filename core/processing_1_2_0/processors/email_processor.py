"""
Email processor for handling email messages.
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
from core.processing_1_2_0.engine.metadata_extractor import MetadataExtractor
from core.processing_1_2_0.metadata import EmailDocumentMetadata
from core.utils.config import config
from core.graph_1_1_0.main import GraphClient
from core.utils.logging import get_logger
import dataclasses
from bs4 import BeautifulSoup
import json

logger = get_logger(__name__)

class EmailProcessor(BaseProcessor):
    """Handles processing of email messages."""
    
    def __init__(self, processing_config: Dict[str, Any]):
        """Initialize the email processor.
        
        Args:
            processing_config: Processing configuration
        """
        super().__init__(processing_config)
        self.graph_client = GraphClient()
        self.processed_folder = config["onedrive"]["processed_emails_folder"]
    
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
            user_email = os.getenv("USER_EMAIL")
            if not user_email:
                raise ProcessingError("USER_EMAIL environment variable not set")
            
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
    
    async def process(self, data: Union[Dict[str, Any], bytes], filename: str = None) -> Dict[str, Any]:
        """Process an email message and save to OneDrive as JSON.
        
        Args:
            data: Email data from Graph API or EML bytes
            filename: (optional) actual filename in OneDrive for lookup
            
        Returns:
            Processed email with cleaned content and metadata
            
        Raises:
            ProcessingError: If processing fails
        """
        try:
            # Process the email
            result = await self._process_impl(data, filename=filename)
            
            # Serialize result to JSON
            json_bytes = json.dumps({
                'subject': result['subject'],
                'metadata': dataclasses.asdict(result['metadata']),
                'attachments': [
                    {
                        'filename': att['filename'],
                        'metadata': dataclasses.asdict(att['metadata'])
                    } for att in result.get('attachments', [])
                ]
            }, ensure_ascii=False, indent=2).encode('utf-8')
            
            # Use .json extension for the filename
            base_filename = os.path.splitext(result['filename'])[0]
            json_filename = f"{base_filename}.json"
            
            # Upload the JSON file
            await self._upload_to_onedrive(json_filename, json_bytes)
            # Don't overwrite the one_drive_url from the original .eml file
            
            # Create metadata files for attachments
            for attachment in result.get('attachments', []):
                # Create a JSON metadata file for the attachment
                att_metadata_bytes = json.dumps(
                    dataclasses.asdict(attachment['metadata']),
                    ensure_ascii=False,
                    indent=2
                ).encode('utf-8')
                
                # Save metadata file alongside the attachment
                att_metadata_filename = f"{os.path.splitext(attachment['filename'])[0]}.json"
                await self._upload_to_onedrive(
                    att_metadata_filename,
                    att_metadata_bytes,
                    folder=config["onedrive"]["documents_folder"]
                )
            
            return result
            
        except Exception as e:
            logger.error(f"Error saving to OneDrive: {str(e)}")
            raise ProcessingError(f"Failed to save to OneDrive: {str(e)}")
    
    async def _process_impl(self, data: Union[Dict[str, Any], bytes], filename: str = None) -> Dict[str, Any]:
        """Process an email message.
        
        Args:
            data: Email data from Graph API or EML bytes
            filename: (optional) actual filename in OneDrive for lookup
        
        Returns:
            Processed email with cleaned content and metadata
        
        Raises:
            ProcessingError: If processing fails
        """
        try:
            # Handle both EML bytes and Graph API data
            if isinstance(data, bytes):
                eml_bytes = data
                # Generate a filename for the processed JSON
                msg = BytesParser(policy=policy.default).parsebytes(eml_bytes)
                message_id = msg.get('Message-ID', '').strip('<>') or str(uuid.uuid4())
                subject = msg.get('Subject', '')
                safe_subject = ''.join(c for c in subject if c.isalnum() or c in (' ', '_')).rstrip().replace(' ', '_')[:50]
                date_prefix = datetime.now().strftime('%Y-%m-%d')
                json_filename = f"{date_prefix}_{safe_subject}_{message_id}.json"
                
                # Get the webUrl of the original EML file
                web_url = ""
                if filename:
                    try:
                        user_email = os.getenv("USER_EMAIL")
                        if not user_email:
                            raise ProcessingError("USER_EMAIL environment variable not set")
                        access_token = await self.graph_client._get_access_token()
                        headers = {"Authorization": f"Bearer {access_token}"}
                        file_url = f"https://graph.microsoft.com/v1.0/users/{user_email}/drive/root:/{config['onedrive']['emails_folder']}/{filename}"
                        logger.debug(f"Getting file metadata from OneDrive: {file_url}")
                        response = await self.graph_client.client.get(file_url, headers=headers)
                        response.raise_for_status()
                        file_metadata = response.json()
                        logger.debug(f"OneDrive file metadata response: {file_metadata}")
                        web_url = file_metadata.get("webUrl")
                        if not web_url:
                            logger.warning(f"Could not get webUrl for original EML file {filename}")
                        else:
                            logger.debug(f"Got webUrl for original EML file {filename}: {web_url}")
                    except Exception as e:
                        logger.warning(f"Error getting webUrl for original EML file {filename}: {str(e)}")
                
                # Process the EML and set the filename and webUrl
                result = self._process_eml(eml_bytes, web_url)
                result['filename'] = json_filename
                return result
            
            # Extract email content from Graph API data
            subject = data.get('subject', '')
            body = data.get('body', {}).get('content', '')
            content_type = data.get('body', {}).get('contentType', 'text/plain')
            
            # Clean email content
            cleaned_subject = self._clean_text(subject)
            if content_type == 'html':
                # Use BeautifulSoup for HTML-to-text extraction
                soup = BeautifulSoup(body, 'html.parser')
                extracted_text = soup.get_text(separator=' ', strip=True)
                cleaned_body = self._clean_text(extracted_text)
            else:
                cleaned_body = self._clean_text(body)
            
            # Extract text content based on content type
            text_content = cleaned_body
            
            # Extract additional metadata
            additional_metadata = self._extract_email_metadata(data)
            
            # Generate base metadata
            metadata = self._generate_metadata(
                content_type=content_type,
                filename=f"email_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                size=len(text_content.encode()),
                source='email'
            )
            
            # Update metadata with email-specific fields
            metadata.update(additional_metadata)
            
            # Remove 'parent_id' if present in metadata
            if 'parent_id' in metadata:
                metadata['parent_email_id'] = metadata.pop('parent_id')
            
            # Only keep fields that are valid for EmailDocumentMetadata
            valid_fields = set(f.name for f in dataclasses.fields(EmailDocumentMetadata))
            filtered_metadata = {k: v for k, v in metadata.items() if k in valid_fields}
            
            # Create email metadata object
            email_metadata = EmailDocumentMetadata(
                **filtered_metadata,
                text_content=text_content
            )
            
            # Process attachments if any
            attachments = self._process_attachments(data.get('attachments', []), metadata['document_id'])
            
            logger.info(f"Successfully processed email: {subject}")
            return {
                'subject': cleaned_subject,
                'body': cleaned_body,
                'filename': metadata['filename'],
                'metadata': email_metadata,
                'attachments': attachments
            }
        except Exception as e:
            logger.error(f"Error processing email: {str(e)}")
            raise ProcessingError(f"Failed to process email: {str(e)}")
    
    def _process_eml(self, eml_bytes: bytes, web_url: str = "") -> Dict[str, Any]:
        """Process an EML file.
        
        Args:
            eml_bytes: Raw EML file content
            web_url: URL of the original EML file in OneDrive
            
        Returns:
            Processed email with cleaned content and metadata
        """
        try:
            msg = BytesParser(policy=policy.default).parsebytes(eml_bytes)
            
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
            
            # Process attachments
            attachments = []
            attachment_ids = []
            for part in msg.iter_attachments():
                att_bytes = part.get_content()
                att_filename = part.get_filename() or f'attachment_{uuid.uuid4().hex}'
                att_content_type = part.get_content_type()
                att_size = len(att_bytes) if att_bytes else 0
                att_doc_id = str(uuid.uuid4())
                attachment_ids.append(att_doc_id)
                
                # Create a safe filename with date prefix and parent email info
                safe_subject = ''.join(c for c in subject if c.isalnum() or c in (' ', '_')).rstrip().replace(' ', '_')[:30]
                date_prefix = date[:10].replace(':', '-') if date else datetime.now().strftime('%Y-%m-%d')
                safe_filename = f"{date_prefix}_email_{safe_subject}_{att_filename}"
                
                # Save attachment as raw document
                try:
                    att_url = self._upload_to_onedrive(
                        safe_filename,
                        att_bytes,
                        folder=config["onedrive"]["documents_folder"]  # Save to documents_1
                    )
                except Exception as e:
                    logger.error(f"Error saving attachment {att_filename}: {str(e)}")
                    att_url = ""
                
                att_metadata = EmailDocumentMetadata(
                    document_id=att_doc_id,
                    type="document",
                    filename=safe_filename,
                    one_drive_url=att_url,
                    created_at=datetime.now().isoformat(),
                    size=att_size,
                    content_type=att_content_type,
                    source="email",
                    is_attachment=True,
                    parent_email_id=message_id,
                    tags=[],
                    text_content=None
                )
                
                attachments.append({
                    "filename": safe_filename,
                    "bytes": att_bytes,
                    "metadata": att_metadata
                })
            
            # Create email metadata
            email_metadata = EmailDocumentMetadata(
                document_id=message_id,
                type="email",
                filename=None,  # To be set after naming
                one_drive_url=web_url,  # Use the webUrl from the original EML file
                created_at=datetime.now().isoformat(),
                size=len(eml_bytes),
                content_type="message/rfc822",
                source="email",
                is_attachment=False,
                parent_email_id=None,
                message_id=message_id,
                subject=subject,
                from_=from_email,
                to=to_emails,
                cc=cc_emails,
                date=date,
                attachments=attachment_ids,
                tags=[],
                text_content=text_content
            )
            
            # Generate a safe filename
            safe_subject = ''.join(c for c in subject if c.isalnum() or c in (' ', '_')).rstrip().replace(' ', '_')[:50]
            date_prefix = date[:10].replace(':', '-') if date else datetime.now().strftime('%Y-%m-%d')
            new_filename = f"{date_prefix}_{safe_subject}_{message_id}.json"
            email_metadata.filename = new_filename
            
            # Return structure matching process_impl
            return {
                "subject": subject,
                "body": text_content,
                "filename": new_filename,
                "metadata": email_metadata,
                "attachments": attachments
            }
            
        except Exception as e:
            logger.error(f"Error processing EML content: {str(e)}")
            raise ProcessingError(f"Failed to process EML content: {str(e)}")
    
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
        if content_type not in config.CONTENT_TYPES:
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
    
    def _process_attachments(self, attachments: List[Dict[str, Any]], parent_id: str) -> List[Dict[str, Any]]:
        """Process email attachments.
        
        Args:
            attachments: List of attachment data
            parent_id: ID of the parent email
            
        Returns:
            List of processed attachments
        """
        processed_attachments = []
        for attachment in attachments:
            try:
                # Add parent email ID to attachment data
                attachment['parent_email_id'] = parent_id
                
                # Process attachment using attachment processor
                processed = self.attachment_processor.process(attachment)
                processed_attachments.append(processed)
            except Exception as e:
                logger.error(f"Error processing attachment {attachment.get('name', 'unknown')}: {str(e)}")
                continue
        
        return processed_attachments 