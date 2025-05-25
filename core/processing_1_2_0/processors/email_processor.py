"""
Email processor for handling email messages.

This module provides functionality to process email messages (.eml format),
extract their content and metadata, and store processed results in OneDrive
via Microsoft Graph API.
"""

from typing import Dict, Any, List, Union, Optional, Set
import logging
from datetime import datetime, timedelta
import uuid
import email
from email import policy
from email.parser import BytesParser
from email.utils import parsedate_to_datetime
import re
from html import unescape
import os
import unicodedata
from core.processing_1_2_0.engine.base import BaseProcessor, ProcessingError, ValidationError
from core.processing_1_2_0.engine.text_extractor import TextExtractor
from core.graph_1_1_0.metadata_extractor import MetadataExtractor
from core.graph_1_1_0.metadata import EmailDocumentMetadata
from core.utils.config import config, PROCESSING_CONFIG, CONTENT_TYPES
from core.graph_1_1_0.main import GraphClient
from core.utils.logging import get_logger
import dataclasses
from bs4 import BeautifulSoup
import json
import asyncio
from core.utils.filename_utils import create_hybrid_filename
from core.utils.onedrive_utils import load_json_file, save_json_file

logger = get_logger(__name__)

# Current schema version for email metadata
SCHEMA_VERSION = "1.0.0"

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

@dataclasses.dataclass
class ProcessingState:
    """Tracks the state of email processing for delta updates."""
    processed_ids: Set[str] = dataclasses.field(default_factory=set)
    last_processed_date: Optional[datetime] = None
    schema_version: str = SCHEMA_VERSION
    deleted_ids: Set[str] = dataclasses.field(default_factory=set)

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
        self.config = processor_config or PROCESSING_CONFIG
        self.metadata_extractor = MetadataExtractor()
        self.text_extractor = TextExtractor()
        self.graph_client = GraphClient()
        self.emails_folder = config["onedrive"]["emails_folder"]
        self.attachments_folder = config["onedrive"]["attachments_folder"]
        self.processed_emails_folder = config["onedrive"]["processed_emails_folder"]
        self.state_file = f"{self.processed_emails_folder}/processing_state.json"
        self.processing_state = ProcessingState()
        logger.info(f"EmailProcessor initialized with folders: emails={self.emails_folder}, attachments={self.attachments_folder}")

    async def load_processing_state(self) -> None:
        """Load the processing state from OneDrive."""
        try:
            state_path = config["onedrive"]["file_list"]
            state_data = await load_json_file(state_path)
            self.processing_state = ProcessingState(
                processed_ids=set(state_data.get('processed_ids', [])),
                last_processed_date=datetime.fromisoformat(state_data.get('last_processed_date')) if state_data.get('last_processed_date') else None,
                schema_version=state_data.get('schema_version', SCHEMA_VERSION),
                deleted_ids=set(state_data.get('deleted_ids', []))
            )
            logger.info(f"Loaded processing state: {len(self.processing_state.processed_ids)} processed, schema version {self.processing_state.schema_version}")
        except Exception as e:
            logger.warning(f"Could not load processing state, starting fresh: {str(e)}")

    async def save_processing_state(self) -> None:
        """Save the current processing state to OneDrive."""
        try:
            state_path = config["onedrive"]["file_list"]
            state_data = {
                'processed_ids': list(self.processing_state.processed_ids),
                'last_processed_date': self.processing_state.last_processed_date.isoformat() if self.processing_state.last_processed_date else None,
                'schema_version': self.processing_state.schema_version,
                'deleted_ids': list(self.processing_state.deleted_ids)
            }
            await save_json_file(state_path, state_data)
            logger.info("Saved processing state")
        except Exception as e:
            logger.error(f"Failed to save processing state: {str(e)}")

    async def process_delta(self, since: Optional[datetime] = None) -> Dict[str, Any]:
        """Process new or modified emails since the last run.
        
        Args:
            since: Optional datetime to process emails from
            
        Returns:
            Processing statistics
        """
        await self.load_processing_state()
        
        # Use provided date or last processed date
        start_date = since or self.processing_state.last_processed_date or (datetime.now() - timedelta(days=1))
        
        stats = {
            'processed': 0,
            'updated': 0,
            'deleted': 0,
            'errors': 0
        }

        try:
            # Get list of current email files
            current_files = await self.graph_client.list_files(
                config["user"]["email"],
                self.processed_emails_folder
            )
            current_ids = {self._extract_id_from_filename(f) for f in current_files if f.endswith('.json')}
            
            # Detect deletions
            deleted_ids = self.processing_state.processed_ids - current_ids
            self.processing_state.deleted_ids.update(deleted_ids)
            stats['deleted'] = len(deleted_ids)
            
            # Process each file
            for file_name in current_files:
                if not file_name.endswith('.json'):
                    continue
                    
                try:
                    file_path = f"{self.processed_emails_folder}/{file_name}"
                    content = await self.graph_client.download_file(
                        config["user"]["email"],
                        file_path
                    )
                    metadata = json.loads(content)
                    
                    # Check if needs reprocessing due to schema change
                    if self._needs_reprocessing(metadata):
                        await self._reprocess_email(metadata)
                        stats['updated'] += 1
                    
                    self.processing_state.processed_ids.add(metadata['document_id'])
                    stats['processed'] += 1
                    
                except Exception as e:
                    logger.error(f"Error processing {file_name}: {str(e)}")
                    stats['errors'] += 1
            
            # Update state
            self.processing_state.last_processed_date = datetime.now()
            await self.save_processing_state()
            
            return stats
            
        except Exception as e:
            logger.error(f"Error in process_delta: {str(e)}")
            raise ProcessingError(f"Delta processing failed: {str(e)}")

    def _needs_reprocessing(self, metadata: Dict[str, Any]) -> bool:
        """Check if an email needs reprocessing due to schema changes.
        
        Args:
            metadata: Email metadata
            
        Returns:
            True if reprocessing is needed
        """
        # Check schema version
        if 'schema_version' not in metadata or metadata['schema_version'] != SCHEMA_VERSION:
            return True
            
        # Check for required fields in current schema
        required_fields = {
            'document_id', 'type', 'filename', 'one_drive_url', 'created_at',
            'source', 'is_attachment', 'message_id', 'subject', 'from_',
            'to', 'cc', 'date', 'text_content', 'attachments'
        }
        
        return not all(field in metadata for field in required_fields)

    async def _reprocess_email(self, old_metadata: Dict[str, Any]) -> None:
        """Reprocess an email with schema updates.
        
        Args:
            old_metadata: Previous email metadata
        """
        try:
            # Add new required fields
            updated_metadata = old_metadata.copy()
            updated_metadata['schema_version'] = SCHEMA_VERSION
            
            # Add any new required fields with defaults
            if 'text_content' not in updated_metadata:
                updated_metadata['text_content'] = ""
            if 'attachments' not in updated_metadata:
                updated_metadata['attachments'] = []
            
            # Save updated metadata
            file_path = f"{self.processed_emails_folder}/{updated_metadata['filename']}"
            await self._save_processed_document(file_path, updated_metadata)
            
        except Exception as e:
            logger.error(f"Failed to reprocess email {old_metadata.get('document_id')}: {str(e)}")
            raise ProcessingError(f"Reprocessing failed: {str(e)}")

    def _extract_id_from_filename(self, filename: str) -> Optional[str]:
        """Extract document ID from filename.
        
        Args:
            filename: Filename to parse
            
        Returns:
            Document ID if found, None otherwise
        """
        try:
            # Filename format: date_subject_id.json
            parts = filename.rsplit('_', 1)
            if len(parts) == 2:
                return parts[1].replace('.json', '')
        except Exception:
            pass
        return None

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
                user_email = self.config["user"]["email"] if "user" in self.config else config["user"]["email"]
                tenant = user_email.split('@')[1]
                default_outlook_url = f"https://outlook.office.com/mail/inbox/id/{message_id}"
            
            # Create email metadata
            email_metadata = EmailDocumentMetadata(
                document_id=message_id,
                type="email",
                filename=None,  # To be set after naming
                source_url=graph_metadata.get("webUrl", default_outlook_url),
                is_attachment=False,
                parent_email_id=None,
                message_id=message_id,
                subject=subject,
                from_=from_email,
                recipients=to_emails + cc_emails,  # Combine both lists
                date=date,
                title="",  # Blank for emails
                author="",  # Blank for emails
                attachments=[],  # Will store attachment IDs
                tags=[],         # Fill as needed
                text_content=text_content
            )
            
            # Generate a safe filename
            safe_subject = ''.join(c for c in subject if c.isalnum() or c in (' ', '_')).rstrip().replace(' ', '_')[:50]
            date_prefix = date[:10].replace(':', '-') if date else datetime.now().strftime('%Y-%m-%d')
            new_filename = f"{date_prefix}_{safe_subject}_{message_id}.json"
            email_metadata.filename = new_filename
            
            # Save email metadata and get OneDrive webUrl
            try:
                # First, try to verify the OneDrive URL isn't empty
                if not email_metadata.source_url or email_metadata.source_url == "":
                    # Generate a proper SharePoint URL for the file in OneDrive
                    sharepoint_domain = "tassehcapital-my.sharepoint.com"  # Get from config if available
                    user_email_domain = user_email.split('@')[1]
                    user_name = user_email.split('@')[0]
                    folder_path = self.processed_emails_folder
                    onedrive_url = f"https://{sharepoint_domain}/personal/{user_name}_{user_email_domain}/Documents/{folder_path}/{new_filename}"
                    email_metadata.source_url = onedrive_url
                
                json_content = email_metadata.to_json()
                
                # Use proper upload_file method instead of non-existent save_email_content_to_onedrive
                file_path = f"{self.processed_emails_folder}/{new_filename}"
                user_email = config["user"]["email"]
                try:
                    upload_response = await self.graph_client.upload_file(
                        user_email,
                        file_path,
                        json_content.encode('utf-8')
                    )
                    if not upload_response:
                        raise ProcessingError("Upload response was empty")
                    logger.info(f"Successfully uploaded email metadata to {file_path}")
                except Exception as e:
                    logger.error(f"Failed to upload email metadata to {file_path}: {str(e)}")
                    raise ProcessingError(f"Failed to upload email metadata: {str(e)}")
                
                # Generate a proper SharePoint URL for the file in OneDrive
                # The upload_response might not contain the full OneDrive URL we need
                sharepoint_domain = "tassehcapital-my.sharepoint.com"  # Get from config if available
                user_email_domain = user_email.split('@')[1]
                user_name = user_email.split('@')[0]
                onedrive_url = f"https://{sharepoint_domain}/personal/{user_name}_{user_email_domain}/Documents/{file_path}"
                
                # Set the OneDrive URL in metadata - ensure it's never blank
                if upload_response and 'https://' in upload_response:
                    email_metadata.source_url = upload_response
                else:
                    email_metadata.source_url = onedrive_url
                
                # Add debugging to verify the URL is set
                logger.debug(f"OneDrive URL for email: {email_metadata.source_url}")
                
            except Exception as e:
                logger.error(f"Error uploading email metadata: {str(e)}")
                # Still continue processing even if upload fails
            
            # Extract attachment info but delegate processing to the AttachmentProcessor
            attachment_info = []
            for part in msg.walk():
                # If the part is an attachment, extract its information
                if part.get_content_disposition() == 'attachment':
                    try:
                        attachment_filename = part.get_filename()
                        if not attachment_filename:
                            continue
                            
                        attachment_content = part.get_payload(decode=True)
                        if not attachment_content:
                            continue
                            
                        content_type = part.get_content_type()
                        if content_type.startswith('image/'):
                            # Skip image attachments
                            logger.info(f"Skipping image attachment: {attachment_filename}")
                            continue
                            
                        # Create a hybrid filename
                        att_ext = os.path.splitext(attachment_filename)[1]
                        safe_name = ''.join(c for c in attachment_filename if c.isalnum() or c in (' ', '_', '.', '-')).rstrip()
                        att_id = str(uuid.uuid4())[:8]
                        safe_att_filename = f"{date_prefix}_{safe_name}_{att_id}{att_ext}"
                        
                        # Save attachment directly to the attachments folder
                        att_path = os.path.join(self.attachments_folder, safe_att_filename)
                        
                        # Upload the attachment to OneDrive
                        await self._upload_to_onedrive(
                            safe_att_filename,
                            attachment_content,
                            self.attachments_folder
                        )
                        
                        # Add attachment ID to email metadata
                        email_metadata.attachments.append(att_id)
                        
                        # Create companion JSON with minimal metadata (AttachmentProcessor will enhance when processing)
                        attachment_min_metadata = {
                            'document_id': att_id,
                            'type': 'attachment',
                            'filename': safe_att_filename,
                            'original_filename': attachment_filename,
                            'one_drive_url': '',
                            'created_at': datetime.now().isoformat(),
                            'size': len(attachment_content),
                            'content_type': content_type,
                            'source': 'email',
                            'is_attachment': True,
                            'parent_email_id': message_id,
                            # Add email context that will be useful for the attachment
                            'parent_email_subject': subject,
                            'parent_email_from': from_email,
                            'parent_email_date': date
                        }
                        
                        # Save companion JSON
                        json_filename = f"{safe_att_filename}.json"
                        json_content = json.dumps(attachment_min_metadata, indent=2, cls=DateTimeEncoder)
                        await self._upload_to_onedrive(
                            json_filename,
                            json_content.encode('utf-8'),
                            self.attachments_folder
                        )
                        
                        # Add to attachment info list
                        attachment_info.append({
                            'id': att_id,
                            'filename': safe_att_filename,
                            'path': att_path
                        })
                        
                    except Exception as e:
                        logger.error(f"Error extracting attachment {part.get_filename() or 'unknown'}: {str(e)}")
            
            # Update email metadata after processing attachments
            if attachment_info:
                # Re-upload the email metadata with updated attachment list
                email_metadata.filename = new_filename
                json_content = email_metadata.to_json()
                file_path = f"{self.processed_emails_folder}/{new_filename}"
                await self.graph_client.upload_file(
                    user_email,
                    file_path,
                    json_content.encode('utf-8')
                )
            
            # Return the processed email data with metadata
            return {
                'email_id': message_id,
                'metadata': email_metadata.to_dict(),
                'attachments': attachment_info,
                'text_content': text_content
            }
            
        except Exception as e:
            logger.error(f"Error processing email: {str(e)}")
            raise ProcessingError(f"Failed to process email: {str(e)}")
    
    def _extract_text_content(self, msg: email.message.Message) -> str:
        """Extract text content from an email message.
        
        Args:
            msg: Email message
            
        Returns:
            Extracted text content
        """
        text_content = ""
        
        # First try to find a text/plain part
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == 'text/plain':
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or 'utf-8'
                    try:
                        text = payload.decode(charset, errors='replace')
                        text_content = self._clean_text(text)
                        break
                    except UnicodeDecodeError:
                        continue
        
        # If no text/plain part, try text/html
        if not text_content:
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == 'text/html':
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or 'utf-8'
                        try:
                            html = payload.decode(charset, errors='replace')
                            soup = BeautifulSoup(html, 'html.parser')
                            text_content = self._clean_text(soup.get_text())
                            break
                        except UnicodeDecodeError:
                            continue
        
        return text_content
    
    def _parse_email_addresses(self, addresses: List[str]) -> List[str]:
        """Parse email addresses from a list of address strings.
        
        Args:
            addresses: List of address strings
            
        Returns:
            List of parsed email addresses
        """
        result = []
        for address in addresses:
            # Simple regex to extract email addresses
            matches = re.findall(r'[\w\.-]+@[\w\.-]+', address)
            result.extend(matches)
        return result
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text content.
        
        Args:
            text: Raw text content
            
        Returns:
            Cleaned text content
        """
        if not text:
            return ""
            
        # Decode HTML entities
        text = unescape(text)
        
        # Common email signature and footer patterns
        signature_patterns = [
            # Email signatures
            r'--+\s*\n.*?Sent from .*?$',
            r'--+\s*\n.*?CONFIDENTIAL.*?$',
            r'--+\s*\n.*?NOTICE:.*?$',
            r'--+\s*\n.*?Disclaimer:.*?$',
            r'--+\s*\n.*?This email.*?$',
            r'--+\s*\n.*?Please consider.*?$',
            r'--+\s*\n.*?Best regards.*?$',
            r'--+\s*\n.*?Regards.*?$',
            r'--+\s*\n.*?Thanks.*?$',
            r'--+\s*\n.*?Cheers.*?$',
            r'--+\s*\n.*?Kind regards.*?$',
            r'--+\s*\n.*?Yours sincerely.*?$',
            r'--+\s*\n.*?Yours truly.*?$',
            r'--+\s*\n.*?Best wishes.*?$',
            r'--+\s*\n.*?Sincerely.*?$',
            r'--+\s*\n.*?Warm regards.*?$',
            r'--+\s*\n.*?Best.*?$',
            r'--+\s*\n.*?Regards.*?$',
            r'--+\s*\n.*?Thanks.*?$',
            r'--+\s*\n.*?Cheers.*?$',
            r'--+\s*\n.*?Kind regards.*?$',
            r'--+\s*\n.*?Yours sincerely.*?$',
            r'--+\s*\n.*?Yours truly.*?$',
            r'--+\s*\n.*?Best wishes.*?$',
            r'--+\s*\n.*?Sincerely.*?$',
            r'--+\s*\n.*?Warm regards.*?$',
            # Common footer patterns
            r'--+\s*\n.*?CONFIDENTIALITY NOTICE.*?$',
            r'--+\s*\n.*?PRIVACY NOTICE.*?$',
            r'--+\s*\n.*?LEGAL NOTICE.*?$',
            r'--+\s*\n.*?DISCLAIMER.*?$',
            r'--+\s*\n.*?This message.*?$',
            r'--+\s*\n.*?This email.*?$',
            r'--+\s*\n.*?Please note.*?$',
            r'--+\s*\n.*?This communication.*?$',
            r'--+\s*\n.*?This transmission.*?$',
            r'--+\s*\n.*?This e-mail.*?$',
            # Social media and contact info
            r'--+\s*\n.*?LinkedIn.*?$',
            r'--+\s*\n.*?Twitter.*?$',
            r'--+\s*\n.*?Facebook.*?$',
            r'--+\s*\n.*?Instagram.*?$',
            r'--+\s*\n.*?Phone:.*?$',
            r'--+\s*\n.*?Mobile:.*?$',
            r'--+\s*\n.*?Tel:.*?$',
            r'--+\s*\n.*?Fax:.*?$',
            r'--+\s*\n.*?Web:.*?$',
            r'--+\s*\n.*?Website:.*?$',
            r'--+\s*\n.*?www\..*?$',
            r'--+\s*\n.*?http.*?$',
            # Company info
            r'--+\s*\n.*?Company.*?$',
            r'--+\s*\n.*?Address:.*?$',
            r'--+\s*\n.*?Registered.*?$',
            r'--+\s*\n.*?VAT.*?$',
            r'--+\s*\n.*?Reg No.*?$',
            r'--+\s*\n.*?ABN.*?$',
            r'--+\s*\n.*?ACN.*?$',
            # Forwarded email markers
            r'--+\s*\n.*?Forwarded by.*?$',
            r'--+\s*\n.*?Begin forwarded message.*?$',
            r'--+\s*\n.*?From:.*?$',
            r'--+\s*\n.*?Date:.*?$',
            r'--+\s*\n.*?Subject:.*?$',
            r'--+\s*\n.*?To:.*?$',
            r'--+\s*\n.*?Cc:.*?$',
            r'--+\s*\n.*?Bcc:.*?$',
        ]
        
        # Remove signatures and footers
        for pattern in signature_patterns:
            text = re.sub(pattern, '', text, flags=re.DOTALL | re.IGNORECASE)
        
        # Remove multiple consecutive whitespace (including newlines)
        if self.config.get("TEXT_CLEANING", {}).get("REMOVE_EXTRA_WHITESPACE", True):
            text = re.sub(r'\s+', ' ', text)
        
        # Normalize line endings
        if self.config.get("TEXT_CLEANING", {}).get("NORMALIZE_LINE_ENDINGS", True):
            text = text.replace("\r\n", "\n").replace("\r", "\n")
        
        # Remove control characters except newlines and tabs
        if self.config.get("TEXT_CLEANING", {}).get("REMOVE_CONTROL_CHARS", True):
            text = ''.join(ch for ch in text if ch == '\n' or ch == '\t' or not unicodedata.category(ch).startswith('C'))
        
        # Remove any remaining dashes that might be part of signatures
        text = re.sub(r'--+\s*$', '', text, flags=re.MULTILINE)
        
        # Remove any remaining empty lines
        text = re.sub(r'\n\s*\n', '\n', text)
        
        # Remove any remaining whitespace at the start and end
        return text.strip()
    
    async def close(self):
        """Close any open resources."""
        await self.graph_client.close()
    
    async def _upload_to_onedrive(self, filename: str, content: bytes, folder: str = "") -> str:
        """Upload content to OneDrive.
        
        Args:
            filename: Name of the file to upload
            content: Content to upload
            folder: Folder to upload to
            
        Returns:
            OneDrive URL of the uploaded file
        """
        try:
            # Determine the full path for the file
            if folder:
                file_path = f"{folder}/{filename}"
            else:
                file_path = filename
                
            # Upload the file
            user_email = config["user"]["email"]
            return await self.graph_client.upload_file(
                user_email,
                file_path,
                content
            )
        except Exception as e:
            logger.error(f"Error uploading to OneDrive: {str(e)}")
            raise ProcessingError(f"Failed to upload to OneDrive: {str(e)}")
    
    async def _process_impl(self, data: Union[Dict[str, Any], bytes], filename: str = None) -> Dict[str, Any]:
        """Implementation of the email processing logic.
        
        Args:
            data: Raw email data (either bytes or dict)
            filename: Optional filename for the processed output
            
        Returns:
            Processed email data
            
        Raises:
            ProcessingError: If processing fails
        """
        try:
            # Handle byte data (raw EML)
            if isinstance(data, bytes):
                return await self._process_email(data, {})
            
            # Handle dict data (from Graph API)
            elif isinstance(data, dict):
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
                    f"{self.processed_emails_folder}/{filename}",
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
    
    async def file_exists(self, file_path: str) -> bool:
        """Check if a file exists in OneDrive.
        
        Args:
            file_path: Path to the file in OneDrive
            
        Returns:
            bool: True if the file exists, False otherwise
        """
        try:
            user_email = config["user"]["email"]
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