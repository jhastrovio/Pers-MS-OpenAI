"""
Microsoft Graph API Client for OneDrive and Email operations.

This module provides a comprehensive client for interacting with Microsoft Graph API,
including email retrieval, OneDrive file operations, and authentication management.
"""

import asyncio
import json
import os
from datetime import datetime, timedelta
import tempfile
import logging
from typing import Dict, Any, List, Optional
import httpx
from msal import ConfidentialClientApplication

from core.utils.config import config
from core.graph_1_1_0.metadata import EmailDocumentMetadata
from core.graph_1_1_0.metadata_extractor import MetadataExtractor
from core.utils.filename_utils import create_hybrid_filename

logger = logging.getLogger(__name__)

# JSON encoder for datetime objects
class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

class GraphClient:
    """Client for interacting with Microsoft Graph API."""
    
    def __init__(self):
        """Initialize the Graph client with authentication."""
        # Use environment variables directly if config doesn't have azure section
        if 'azure' in config:
            self.client_id = config['azure']['client_id']
            self.client_secret = config['azure']['client_secret']
            self.tenant_id = config['azure']['tenant_id']
        else:
            # Fallback to environment variables
            import os
            self.client_id = os.getenv('CLIENT_ID')
            self.client_secret = os.getenv('CLIENT_SECRET')
            self.tenant_id = os.getenv('TENANT_ID')
        
        # Define required scopes for Microsoft Graph API
        self.scopes = ["https://graph.microsoft.com/.default"]
        
        # Initialize MSAL client
        self.msal_client = ConfidentialClientApplication(
            client_id=self.client_id,
            client_credential=self.client_secret,
            authority=f"https://login.microsoftonline.com/{self.tenant_id}"
        )

        # Initialize httpx client with redirect following enabled
        self.client = httpx.AsyncClient(follow_redirects=True, timeout=30.0)
        self._access_token = None
        self._token_expiry = None

    async def __aenter__(self) -> "GraphClient":
        """Enter the async context manager and return self."""
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        """Close the underlying HTTP client when exiting the context."""
        await self.close()
        
    async def _get_access_token(self):
        """Get a valid access token, refreshing if necessary."""
        if not self._access_token or (self._token_expiry and datetime.now() >= self._token_expiry):
            await self._refresh_token()
        return self._access_token
    
    async def _refresh_token(self):
        """Refresh the access token using client credentials."""
        try:
            # Use MSAL for token management
            token_result = self.msal_client.acquire_token_for_client(scopes=self.scopes)
            if "access_token" not in token_result:
                error_msg = f"Could not obtain access token: {json.dumps(token_result)}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)
            
            self._access_token = token_result["access_token"]
            self._token_expiry = datetime.now() + timedelta(seconds=token_result.get('expires_in', 3600) - 300)
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

    # CONSOLIDATED METHOD: Alternative name for compatibility
    async def list_files_in_folder(self, folder_path: str) -> List[Dict[str, Any]]:
        """List files in a specific OneDrive folder (compatibility method).
        
        Args:
            folder_path: The path to the folder in OneDrive
            
        Returns:
            List of file metadata objects
        """
        user_email = config.get("user", {}).get("email") or os.getenv('user_email')
        if not user_email:
            raise ValueError("User email not found in config or environment")
        return await self.list_files(user_email, folder_path)
    
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
            
            logger.debug(f"Requesting file content from: {url}")
            
            # Make the request with redirects enabled
            response = await self.client.get(url, headers=headers)
            
            logger.debug(f"Response status: {response.status_code}")
            logger.debug(f"Response headers: {dict(response.headers)}")
            
            response.raise_for_status()
            
            # Check if we got actual content
            if response.content:
                logger.debug(f"Successfully downloaded file: {file_path} ({len(response.content)} bytes)")
                return response.content
            else:
                logger.warning(f"File download resulted in empty content: {file_path}")
                return None
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error downloading file {file_path}: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Error getting content of file {file_path}: {str(e)}")
            return None

    # CONSOLIDATED METHOD: Alternative name for compatibility
    async def download_file_from_onedrive(self, folder_path: str, file_name: str) -> bytes:
        """Download a file from OneDrive by folder_path and file_name (compatibility method).
        
        Args:
            folder_path: The folder path in OneDrive
            file_name: The name of the file to download
            
        Returns:
            File content as bytes
        """
        user_email = config.get("user", {}).get("email") or os.getenv('user_email')
        if not user_email:
            raise ValueError("User email not found in config or environment")
        
        # Combine folder path and file name
        full_path = f"{folder_path.strip('/')}/{file_name}"
        return await self.get_file_content(user_email, full_path)

    # CONSOLIDATED METHOD: Email retrieval functionality
    async def get_emails(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieve emails from user's mailbox.
        
        Args:
            limit: Maximum number of emails to retrieve
            
        Returns:
            List of email objects with metadata
        """
        logger.info(f"Retrieving {limit} emails from mailbox")
        access_token = await self._get_access_token()
        headers = {"Authorization": f"Bearer {access_token}"}
        
        try:
            user_email = config.get("user", {}).get("email") or os.getenv('user_email')
            if not user_email:
                raise ValueError("User email not found in config or environment")
                
            response = await self.client.get(
                f'https://graph.microsoft.com/v1.0/users/{user_email}/messages',
                headers=headers,
                params={"$top": limit}
            )
            response.raise_for_status()
            data = response.json()
            return data.get('value', [])
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error occurred: {str(e)}")
            logger.error(f"Response content: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error retrieving emails: {str(e)}")
            raise

    # CONSOLIDATED METHOD: Document retrieval functionality  
    async def get_documents(self) -> List[Dict[str, Any]]:
        """Retrieve documents from OneDrive.
        
        Returns:
            List of document objects with metadata and content.
        """
        logger.info("Retrieving documents from OneDrive")
        access_token = await self._get_access_token()
        headers = {"Authorization": f"Bearer {access_token}"}
        
        try:
            user_email = config.get("user", {}).get("email") or os.getenv('user_email')
            if not user_email:
                raise ValueError("User email not found in config or environment")
                
            response = await self.client.get(
                f'https://graph.microsoft.com/v1.0/users/{user_email}/drive/root/children',
                headers=headers,
                params={"$top": 10}
            )
            response.raise_for_status()
            data = response.json()
            return data.get('value', [])
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error occurred: {str(e)}")
            logger.error(f"Response content: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error retrieving documents: {str(e)}")
            raise

    # CONSOLIDATED METHOD: Save to OneDrive functionality
    async def save_to_onedrive(self, file_path: str, file_name: str, folder: str = None) -> Dict[str, Any]:
        """Upload a file to OneDrive using Microsoft Graph API (compatibility method).

        Args:
            file_path: Local path to the file to upload.
            file_name: Name to give the file in OneDrive.
            folder: Optional folder path in OneDrive. If not provided, uses the default from config.

        Returns:
            Dict containing the response from the upload operation.
        """
        logger.info(f"Uploading file {file_name} to OneDrive")
        
        # Use the folder from config if not provided
        if folder is None:
            folder = config.get("onedrive", {}).get("emails_folder", "emails_1")

        try:
            with open(file_path, "rb") as file:
                content = file.read()
            
            # Use the modern upload_file method that returns the full response
            user_email = config.get("user", {}).get("email") or os.getenv('user_email')
            if not user_email:
                raise ValueError("User email not found in config or environment")
                
            file_response = await self.upload_file_with_response(user_email, f"{folder}/{file_name}", content)
            return file_response
            
        except Exception as e:
            logger.error(f"Error uploading file to OneDrive: {str(e)}")
            raise

    # CONSOLIDATED METHOD: Save email content functionality
    async def save_email_content_to_onedrive(self, email_content: str, file_name: str, folder: str = None) -> dict:
        """Upload email content directly to OneDrive as a file (compatibility method)."""
        logger.info(f"Uploading email content as {file_name} to OneDrive")
        
        if folder is None:
            folder = config.get("onedrive", {}).get("emails_folder", "emails_1")
            
        user_email = config.get("user", {}).get("email") or os.getenv('user_email')
        if not user_email:
            raise ValueError("User email not found in config or environment")
            
        # Use the modern upload_file method that returns the full response
        file_response = await self.upload_file_with_response(
            user_email, 
            f"{folder}/{file_name}", 
            email_content.encode("utf-8")
        )
        return file_response

    async def upload_file(self, user_email: str, file_path: str, content: bytes) -> str:
        """Upload a file to OneDrive.
        
        Args:
            user_email: The email address of the user
            file_path: The path where the file should be saved in OneDrive
            content: The file content as bytes
            
        Returns:
            str: The web URL of the uploaded file
        """
        file_response = await self.upload_file_with_response(user_email, file_path, content)
        return file_response.get("webUrl", "")

    async def upload_file_with_response(self, user_email: str, file_path: str, content: bytes) -> Dict[str, Any]:
        """Upload a file to OneDrive and return the full API response.
        
        Args:
            user_email: The email address of the user
            file_path: The path where the file should be saved in OneDrive
            content: The file content as bytes
            
        Returns:
            Dict: The full Microsoft Graph API response including id, webUrl, etc.
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
            
            # Return the full response data
            file_data = response.json()
            
            # Validate that we got the expected fields
            if not file_data.get("webUrl"):
                logger.error("No webUrl in response: %s", file_data)
                # Try to get the URL from the file metadata
                file_id = file_data.get("id")
                if file_id:
                    file_url = f"https://graph.microsoft.com/v1.0/users/{user_email}/drive/items/{file_id}"
                    file_response = await self.client.get(file_url, headers=headers)
                    file_response.raise_for_status()
                    file_metadata = file_response.json()
                    return file_metadata
                else:
                    raise Exception("Failed to get web URL from OneDrive response")
            
            logger.info(f"Successfully uploaded file to {file_data.get('webUrl')}")
            return file_data
            
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
            user_email = config.get("user", {}).get("email") or os.getenv('user_email')
            if not user_email:
                raise ValueError("User email not found in config or environment")
                
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