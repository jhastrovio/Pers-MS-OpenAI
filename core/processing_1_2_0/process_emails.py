import os
from core.utils.config import config
from core.graph_1_1_0.main import GraphClient
from typing import List, Dict, Any
import httpx
import uuid
import email
from email import policy
from email.parser import BytesParser
from core.processing_1_2_0.metadata import EmailDocumentMetadata
import json
import re
from html import unescape
from datetime import datetime
from email.utils import parsedate_to_datetime

# Unified metadata schema (docstring for reference)
"""
Metadata fields:
- document_id: str
- type: 'email' | 'document'
- filename: str
- one_drive_url: str
- created_at: str (ISO 8601)
- size: int
- content_type: str
- source: str (e.g., 'outlook' for emails, 'onedrive' for docs)
- is_attachment: bool
- parent_email_id: str | None
- parent_document_id: str | None
- message_id: str | None
- subject: str | None
- from: str | None
- to: List[str] | None
- cc: List[str] | None
- date: str | None
- title: str | None
- author: str | None
- last_modified: str | None
- attachments: List[document_id] | None
- tags: List[str] | None
"""

def clean_text_content(text: str) -> str:
    """Clean text content by removing HTML tags, normalizing whitespace, and replacing smart punctuation."""
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
        # Replace any remaining problematic replacement chars (like '')
        text = text.replace('\ufffd', '')
        # Remove any remaining non-printable or non-ASCII characters
        text = ''.join(char for char in text if (char.isprintable() and ord(char) < 128) or char.isspace())
        # Normalize whitespace again
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    except Exception as e:
        print(f"Warning: Error cleaning text content: {str(e)}")
        return text.strip() if text else ""

def parse_email_addresses(addresses: List[str]) -> List[str]:
    """Parse email addresses from a list of address strings."""
    if not addresses:
        return []
    parsed = email.utils.getaddresses(addresses)
    return [addr for name, addr in parsed if addr]

async def list_raw_eml_files(client: GraphClient) -> List[str]:
    """List all .eml files in the OneDrive raw emails folder."""
    folder = config["onedrive"]["emails_folder"]
    user_email = os.getenv("USER_EMAIL")
    url = f"https://graph.microsoft.com/v1.0/users/{user_email}/drive/root:/{folder}:/children"
    access_token = await client._get_access_token()
    headers = {"Authorization": f"Bearer {access_token}"}
    response = await client.client.get(url, headers=headers)
    response.raise_for_status()
    items = response.json().get("value", [])
    eml_files = [item["name"] for item in items if item["name"].lower().endswith(".eml")]
    return eml_files

async def download_eml_file(client: GraphClient, file_name: str) -> bytes:
    """Download a raw .eml file from OneDrive as bytes."""
    folder = config["onedrive"]["emails_folder"]
    user_email = os.getenv("USER_EMAIL")
    url = f"https://graph.microsoft.com/v1.0/users/{user_email}/drive/root:/{folder}/{file_name}:/content"
    access_token = await client._get_access_token()
    headers = {"Authorization": f"Bearer {access_token}"}
    response = await client.client.get(url, headers=headers, follow_redirects=True)
    response.raise_for_status()
    return response.content

async def process_eml_content(eml_bytes: bytes) -> Dict[str, Any]:
    """Parse, clean, and extract metadata and attachments from an .eml file in memory.
    Returns a dict with cleaned eml content, new filename, email metadata, and attachments.
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
        to_emails = parse_email_addresses(to)
        cc_emails = parse_email_addresses(cc)
        from_email = parse_email_addresses([from_])[0] if from_ else ''
        
        # Parse date
        try:
            date = parsedate_to_datetime(date_str).isoformat() if date_str else ''
        except:
            date = ''
        
        # Extract text content
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
        
        # Clean text content
        text_content = clean_text_content(text_content) if text_content else ''
        
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
            
            att_metadata = EmailDocumentMetadata(
                document_id=att_doc_id,
                type="document",
                filename=att_filename,
                one_drive_url="",  # To be filled after upload
                created_at=datetime.now().isoformat(),
                size=att_size,
                content_type=att_content_type,
                source="email",  # Source is email since it came from an email
                is_attachment=True,
                parent_email_id=message_id,
                tags=[],
                text_content=None
            )
            
            attachments.append({
                "filename": att_filename,
                "bytes": att_bytes,
                "metadata": att_metadata
            })
        
        # Create email metadata
        email_metadata = EmailDocumentMetadata(
            document_id=message_id,
            type="email",
            filename=None,  # To be set after naming
            one_drive_url="",  # To be filled after upload
            created_at=datetime.now().isoformat(),
            size=len(eml_bytes),
            content_type="message/rfc822",
            source="email",  # Source is email
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
        new_filename = f"{date_prefix}_{safe_subject}_{message_id}.eml"
        email_metadata.filename = new_filename
        
        return {
            "eml_bytes": eml_bytes,
            "filename": new_filename,
            "metadata": email_metadata,
            "attachments": attachments
        }
        
    except Exception as e:
        raise Exception(f"Error processing email content: {str(e)}")

async def upload_processed_eml(client: GraphClient, file_name: str, eml_bytes: bytes, metadata: EmailDocumentMetadata) -> Dict[str, str]:
    """Upload processed email metadata JSON to the processed_emails_folder in OneDrive."""
    try:
        folder = config["onedrive"]["processed_emails_folder"]
        user_email = os.getenv("USER_EMAIL")
        
        # Upload only the metadata JSON
        meta_filename = file_name.rsplit('.', 1)[0] + ".json"
        meta_upload_url = f"https://graph.microsoft.com/v1.0/users/{user_email}/drive/root:/{folder}/{meta_filename}:/content"
        meta_bytes = metadata.to_json().encode("utf-8")
        
        access_token = await client._get_access_token()
        headers = {"Authorization": f"Bearer {access_token}"}
        
        meta_response = await client.client.put(meta_upload_url, headers=headers, content=meta_bytes)
        meta_response.raise_for_status()
        resp_json = meta_response.json()
        
        # Update metadata with OneDrive info
        metadata.one_drive_url = resp_json.get("webUrl", "")
        metadata.created_at = resp_json.get("createdDateTime", "")
        
        return {
            "one_drive_url": metadata.one_drive_url,
            "created_at": metadata.created_at
        }
        
    except Exception as e:
        raise Exception(f"Error uploading processed email: {str(e)}")

async def upload_attachment(client: GraphClient, file_name: str, attachment_bytes: bytes, metadata: EmailDocumentMetadata) -> Dict[str, str]:
    """Upload an attachment to the processed_documents_folder in OneDrive."""
    try:
        folder = config["onedrive"]["processed_documents_folder"]
        user_email = os.getenv("USER_EMAIL")
        
        # Upload the attachment
        upload_url = f"https://graph.microsoft.com/v1.0/users/{user_email}/drive/root:/{folder}/{file_name}:/content"
        access_token = await client._get_access_token()
        headers = {"Authorization": f"Bearer {access_token}"}
        
        response = await client.client.put(upload_url, headers=headers, content=attachment_bytes)
        response.raise_for_status()
        resp_json = response.json()
        
        # Update metadata with OneDrive info
        metadata.one_drive_url = resp_json.get("webUrl", "")
        metadata.created_at = resp_json.get("createdDateTime", "")
        
        # Upload the metadata JSON
        meta_filename = file_name.rsplit('.', 1)[0] + ".json"
        meta_upload_url = f"https://graph.microsoft.com/v1.0/users/{user_email}/drive/root:/{folder}/{meta_filename}:/content"
        meta_bytes = metadata.to_json().encode("utf-8")
        
        meta_response = await client.client.put(meta_upload_url, headers=headers, content=meta_bytes)
        meta_response.raise_for_status()
        
        return {
            "one_drive_url": metadata.one_drive_url,
            "created_at": metadata.created_at
        }
        
    except Exception as e:
        raise Exception(f"Error uploading attachment: {str(e)}")

async def process_all_emails():
    """Main entry point: process all raw emails in OneDrive and upload processed results."""
    client = GraphClient()
    try:
        # List all .eml files
        eml_files = await list_raw_eml_files(client)
        
        for file_name in eml_files:
            try:
                # Download and process the file
                eml_bytes = await download_eml_file(client, file_name)
                processed = await process_eml_content(eml_bytes)
                
                # Upload the processed email
                result = await upload_processed_eml(
                    client,
                    processed['filename'],
                    processed['eml_bytes'],
                    processed['metadata']
                )
                
                # Upload any attachments
                for attachment in processed['attachments']:
                    await upload_attachment(
                        client,
                        attachment['filename'],
                        attachment['bytes'],
                        attachment['metadata']
                    )
                
                print(f"Processed {file_name} -> {processed['filename']}")
                
            except Exception as e:
                print(f"Error processing {file_name}: {str(e)}")
                continue
                
    except Exception as e:
        print(f"Error in process_all_emails: {str(e)}") 