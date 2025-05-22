"""
Microsoft Graph Integration Module

This module handles all interactions with Microsoft Graph API, including:
- Email retrieval and storage
- OneDrive document synchronization
- Authentication and token management
"""

from typing import List, Dict, Any
import os
from msal import PublicClientApplication, ConfidentialClientApplication
from core.utils.config import get_env_variable, config
from core.utils.logging import get_logger
from core.graph_1_1_0.metadata import EmailDocumentMetadata
from core.graph_1_1_0.metadata_extractor import MetadataExtractor
import httpx
import json
from datetime import datetime, timedelta
import urllib.parse
import re
from core.utils.filename_utils import create_hybrid_filename

logger = get_logger(__name__)

# Custom JSON encoder to handle datetime objects
class DateTimeEncoder(json.JSONEncoder):
    """JSON encoder that converts datetime objects to ISO format strings."""
    def default(self, obj):
        if isinstance(obj, (datetime, timedelta)):
            return obj.isoformat()
        return super().default(obj)

class GraphClient:
    """Client for interacting with Microsoft Graph API."""
    
    def __init__(self):
        """Initialize the Graph client with authentication."""
        self.client = httpx.AsyncClient()
        self._access_token = None
        self._token_expiry = None
        
    async def _get_access_token(self):
        """Get a valid access token, refreshing if necessary."""
        if not self._access_token or (self._token_expiry and datetime.now() >= self._token_expiry):
            await self._refresh_token()
        return self._access_token
    
    async def _refresh_token(self):
        """Refresh the access token using client credentials."""
        try:
            token_url = f"https://login.microsoftonline.com/{config['azure']['tenant_id']}/oauth2/v2.0/token"
            data = {
                'client_id': config['azure']['client_id'],
                'client_secret': config['azure']['client_secret'],
                'scope': 'https://graph.microsoft.com/.default',
                'grant_type': 'client_credentials'
            }
            response = await self.client.post(token_url, data=data)
            response.raise_for_status()
            token_data = response.json()
            self._access_token = token_data['access_token']
            self._token_expiry = datetime.now() + timedelta(seconds=token_data['expires_in'] - 300)
        except Exception as e:
            raise Exception(f"Failed to refresh token: {str(e)}")
    
    async def list_files(self, user_email: str, folder_path: str) -> List[Dict[str, Any]]:
        """List files in a OneDrive folder.
        
        Args:
            user_email: The email address of the user
            folder_path: The path to the folder in OneDrive
            
        Returns:
            List of file metadata objects
        """
        try:
            access_token = await self._get_access_token()
            headers = {"Authorization": f"Bearer {access_token}"}
            
            # Normalize folder path for OneDrive API
            folder_path = folder_path.replace('\\', '/').strip('/')
            url = f"https://graph.microsoft.com/v1.0/users/{user_email}/drive/root:/{folder_path}:/children"
            
            response = await self.client.get(url, headers=headers)
            response.raise_for_status()
            
            return response.json().get("value", [])
            
        except Exception as e:
            logger.error(f"Error listing files in {folder_path}: {str(e)}")
            return []
    
    async def get_file_content(self, user_email: str, file_path: str) -> bytes:
        """Get the content of a file from OneDrive.
        
        Args:
            user_email: The email address of the user
            file_path: The path to the file in OneDrive
            
        Returns:
            File content as bytes
        """
        try:
            access_token = await self._get_access_token()
            headers = {"Authorization": f"Bearer {access_token}"}
            
            # Normalize file path for OneDrive API
            file_path = file_path.replace('\\', '/').strip('/')
            url = f"https://graph.microsoft.com/v1.0/users/{user_email}/drive/root:/{file_path}:/content"
            
            response = await self.client.get(url, headers=headers)
            response.raise_for_status()
            
            return response.content
            
        except Exception as e:
            logger.error(f"Error getting content of file {file_path}: {str(e)}")
            return None
    
    async def fetch_and_store_email(self, user_email: str, message_id: str) -> dict:
        """Fetch an email message and store it in three stages:
        1. Fetch metadata and web URL
        2. Save raw .eml
        3. Save attachments
        
        Args:
            user_email: The email address of the user
            message_id: The ID of the message to fetch
        
        Returns:
            dict: Results including metadata, .eml path, and attachment paths
        """
        try:
            access_token = await self._get_access_token()
            headers = {"Authorization": f"Bearer {access_token}"}
            
            # Stage 1: Fetch message metadata
            metadata_url = f"https://graph.microsoft.com/v1.0/users/{user_email}/messages/{message_id}"
            metadata_response = await self.client.get(metadata_url, headers=headers)
            try:
                metadata_response.raise_for_status()
                raw_metadata = metadata_response.json()
            except Exception as e:
                try:
                    error_body = metadata_response.text
                    logger.error(f"Error response body: {error_body}")
                except Exception:
                    pass
                raise
            
            # Stage 2: Fetch and save raw .eml
            eml_url = f"https://graph.microsoft.com/v1.0/users/{user_email}/messages/{message_id}/$value"
            eml_response = await self.client.get(eml_url, headers=headers)
            eml_response.raise_for_status()
            eml_content = eml_response.content
            
            # Create hybrid filename for .eml
            subject = raw_metadata.get("subject", "No_Subject")
            eml_filename = create_hybrid_filename(message_id, subject, ".eml")
            eml_path = os.path.join(config["onedrive"]["emails_folder"], eml_filename)
            eml_url = await self.upload_file(user_email, eml_path, eml_content)
            
            # Create structured metadata for the email
            email_metadata = EmailDocumentMetadata(
                document_id=message_id,
                type="email",
                filename=eml_filename,
                source_url=eml_url,
                created_at=raw_metadata.get("receivedDateTime", ""),
                size=raw_metadata.get("size", 0),
                content_type="message/rfc822",
                source="outlook",
                is_attachment=False,
                message_id=message_id,
                subject=subject,
                from_=raw_metadata.get("from", {}).get("emailAddress", {}).get("address", ""),
                to=[recipient.get("emailAddress", {}).get("address", "") for recipient in raw_metadata.get("toRecipients", [])],
                cc=[recipient.get("emailAddress", {}).get("address", "") for recipient in raw_metadata.get("ccRecipients", [])],
                date=raw_metadata.get("receivedDateTime", ""),
                text_content=raw_metadata.get("bodyPreview", ""),
                attachments=[]
            )
            
            # Stage 3: Fetch and store attachments if present
            attachment_paths = []
            if raw_metadata.get("hasAttachments"):
                attachments_url = f"https://graph.microsoft.com/v1.0/users/{user_email}/messages/{message_id}/attachments"
                attachments_response = await self.client.get(attachments_url, headers=headers)
                attachments_response.raise_for_status()
                attachments = attachments_response.json().get("value", [])
                
                for attachment in attachments:
                    # Skip image attachments
                    content_type = attachment.get("contentType", "").lower()
                    if content_type.startswith("image/"):
                        logger.info(f"Skipping image attachment: {attachment.get('name', 'unknown')}")
                        continue
                        
                    # Get attachment content
                    att_url = f"https://graph.microsoft.com/v1.0/users/{user_email}/messages/{message_id}/attachments/{attachment['id']}/$value"
                    att_response = await self.client.get(att_url, headers=headers)
                    att_response.raise_for_status()
                    att_content = att_response.content
                    
                    # Create hybrid filename for attachment
                    att_name = attachment["name"]
                    att_ext = os.path.splitext(att_name)[1]
                    att_filename = create_hybrid_filename(
                        f"{message_id}_{attachment['id']}", 
                        att_name,
                        att_ext
                    )
                    att_path = os.path.join(config["onedrive"]["attachments_folder"], att_filename)
                    att_url = await self.upload_file(user_email, att_path, att_content)
                    
                    # Extract metadata for the attachment
                    att_metadata = MetadataExtractor.extract_metadata(att_content, attachment.get("contentType", ""))
                    
                    # Create structured metadata for the attachment
                    attachment_metadata = EmailDocumentMetadata(
                        document_id=attachment["id"],
                        type="document",
                        filename=att_filename,
                        source_url=att_url,
                        created_at=raw_metadata.get("receivedDateTime", ""),
                        size=attachment.get("size", 0),
                        content_type=attachment.get("contentType", ""),
                        source="outlook",
                        is_attachment=True,
                        parent_email_id=message_id,
                        message_id=message_id,
                        subject=subject,
                        from_=raw_metadata.get("from", {}).get("emailAddress", {}).get("address", ""),
                        title=att_metadata.get("title", att_name),
                        author=att_metadata.get("author", ""),
                        last_modified=att_metadata.get("last_modified", ""),
                        text_content=att_metadata.get("text_content", "")
                    )
                    
                    # Save companion JSON file with metadata
                    base_name, ext = os.path.splitext(att_filename)
                    json_filename = f"{base_name}{ext}.json"
                    json_path = os.path.join(config["onedrive"]["attachments_folder"], json_filename)
                    json_content = json.dumps(attachment_metadata.to_dict(), indent=2, cls=DateTimeEncoder)
                    json_url = await self.upload_file(user_email, json_path, json_content.encode('utf-8'))
                    
                    attachment_paths.append({
                        "id": attachment["id"],
                        "name": attachment["name"],
                        "path": att_path,
                        "metadata": attachment_metadata.to_dict(),
                        "metadata_path": json_path,
                        "metadata_url": json_url
                    })
                    
                    # Add attachment ID to email metadata
                    email_metadata.attachments.append(attachment["id"])
            
            return {
                "metadata": email_metadata.to_dict(),
                "eml_path": eml_path,
                "attachments": attachment_paths
            }
            
        except Exception as e:
            raise Exception(f"Failed to fetch and store email: {str(e)}")
        
    async def upload_file(self, user_email: str, file_path: str, content: bytes) -> str:
        """Upload a file to OneDrive.
        
        Args:
            user_email: The email address of the user
            file_path: The path where the file should be saved in OneDrive
            content: The file content as bytes
            
        Returns:
            str: The web URL of the uploaded file
        """
        try:
            access_token = await self._get_access_token()
            
            # Normalize file path for OneDrive (use forward slashes)
            file_path = file_path.replace('\\', '/')
            
            # Determine content type based on file extension
            ext = os.path.splitext(file_path)[1].lower()
            content_type = {
                '.pdf': 'application/pdf',
                '.doc': 'application/msword',
                '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                '.xls': 'application/vnd.ms-excel',
                '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.document',
                '.ppt': 'application/vnd.ms-powerpoint',
                '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
                '.txt': 'text/plain',
                '.csv': 'text/csv',
                '.eml': 'message/rfc822',
                '.json': 'application/json'
            }.get(ext, 'application/octet-stream')
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": content_type
            }
            
            # Ensure the folder exists
            folder_path = os.path.dirname(file_path)
            if folder_path:
                try:
                    # Create folder if it doesn't exist
                    folder_url = f"https://graph.microsoft.com/v1.0/users/{user_email}/drive/root:/{folder_path}"
                    await self.client.get(folder_url, headers=headers)
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 404:
                        # Create the folder
                        create_folder_url = f"https://graph.microsoft.com/v1.0/users/{user_email}/drive/root/children"
                        folder_name = os.path.basename(folder_path)
                        folder_data = {
                            "name": folder_name,
                            "folder": {},
                            "@microsoft.graph.conflictBehavior": "rename"
                        }
                        await self.client.post(create_folder_url, headers=headers, json=folder_data)
            
            # Upload the file
            upload_url = f"https://graph.microsoft.com/v1.0/users/{user_email}/drive/root:/{file_path}:/content"
            logger.info(f"Uploading to URL: {upload_url}")
            logger.info(f"Content-Type: {content_type}")
            logger.info(f"File size: {len(content)} bytes")
            
            response = await self.client.put(upload_url, headers=headers, content=content)
            response.raise_for_status()
            
            # Get the web URL
            file_data = response.json()
            web_url = file_data.get("webUrl")
            if not web_url:
                logger.error("No webUrl in response: %s", file_data)
                # Try to get the URL from the file metadata
                file_id = file_data.get("id")
                if file_id:
                    file_url = f"https://graph.microsoft.com/v1.0/users/{user_email}/drive/items/{file_id}"
                    file_response = await self.client.get(file_url, headers=headers)
                    file_response.raise_for_status()
                    file_metadata = file_response.json()
                    web_url = file_metadata.get("webUrl")
                    if not web_url:
                        raise Exception("Failed to get web URL from OneDrive response")
                else:
                    raise Exception("Failed to get web URL from OneDrive response")
            
            logger.info(f"Successfully uploaded file to {web_url}")
            return web_url
            
        except httpx.HTTPStatusError as e:
            error_data = e.response.json() if e.response.content else {}
            logger.error(f"HTTP error {e.response.status_code} uploading to OneDrive: {error_data}")
            raise Exception(f"HTTP error uploading to OneDrive: {error_data.get('error', {}).get('message', str(e))}")
        except Exception as e:
            logger.error(f"Failed to upload file {file_path}: {str(e)}")
            raise Exception(f"Failed to upload file: {str(e)}")
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
        
    async def file_exists(self, file_path: str) -> bool:
        """Check if a file exists in OneDrive.
        
        Args:
            file_path: Path to the file in OneDrive
            
        Returns:
            bool: True if the file exists, False otherwise
        """
        try:
            user_email = config["user"]["email"]
            access_token = await self._get_access_token()
            headers = {"Authorization": f"Bearer {access_token}"}
            
            # Normalize the path for OneDrive API
            file_path = file_path.replace('\\', '/').strip('/')
            url = f"https://graph.microsoft.com/v1.0/users/{user_email}/drive/root:/{file_path}"
            
            response = await self.client.get(url, headers=headers)
            response.raise_for_status()
            
            # If we get here, the file exists
            return True
            
        except Exception as e:
            logger.debug(f"File check failed for {file_path}: {str(e)}")
            return False 