"""
Microsoft Graph Integration Module

This module handles all interactions with Microsoft Graph API, including:
- Email retrieval and processing
- OneDrive document synchronization
- Authentication and token management
"""

from typing import List, Dict, Any
import os
from msal import PublicClientApplication, ConfidentialClientApplication
from core.utils.config import get_env_variable, config
from core.utils.logging import get_logger
import httpx
import json

logger = get_logger(__name__)

class GraphClient:
    """Client for interacting with Microsoft Graph API."""
    
    def __init__(self):
        """Initialize the Graph client with MSAL authentication."""
        self.client_id = get_env_variable('CLIENT_ID')
        self.client_secret = get_env_variable('CLIENT_SECRET')
        self.tenant_id = get_env_variable('TENANT_ID')
        
        # Define required scopes for Microsoft Graph API
        self.scopes = ["https://graph.microsoft.com/.default"]
        
        # Initialize MSAL client
        self.msal_client = ConfidentialClientApplication(
            client_id=self.client_id,
            client_credential=self.client_secret,
            authority=f"https://login.microsoftonline.com/{self.tenant_id}"
        )
        
        # Create an async httpx client
        self.client = httpx.AsyncClient()
        
    async def _get_access_token(self) -> str:
        """Get a valid access token, refreshing if necessary."""
        token_result = self.msal_client.acquire_token_for_client(scopes=self.scopes)
        if "access_token" not in token_result:
            error_msg = f"Could not obtain access token: {json.dumps(token_result)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        return token_result["access_token"]
        
    async def get_emails(self) -> List[Dict[str, Any]]:
        """Retrieve emails from Microsoft Graph.
        
        Returns:
            List of email objects with metadata and content.
        """
        logger.info("Retrieving emails from Microsoft Graph")
        access_token = await self._get_access_token()
        headers = {"Authorization": f"Bearer {access_token}"}
        
        try:
            user_email = get_env_variable('user_email')
            response = await self.client.get(
                f'https://graph.microsoft.com/v1.0/users/{user_email}/messages',
                headers=headers,
                params={"$top": 10}  # Limit to 10 messages for testing
            )
            data = response.json()
            return data.get('value', [])
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error occurred: {str(e)}")
            logger.error(f"Response content: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error retrieving emails: {str(e)}")
            raise
        
    async def get_documents(self) -> List[Dict[str, Any]]:
        """Retrieve documents from OneDrive.
        
        Returns:
            List of document objects with metadata and content.
        """
        logger.info("Retrieving documents from OneDrive")
        access_token = await self._get_access_token()
        headers = {"Authorization": f"Bearer {access_token}"}
        
        try:
            user_email = get_env_variable('user_email')
            response = await self.client.get(
                f'https://graph.microsoft.com/v1.0/users/{user_email}/drive/root/children',
                headers=headers,
                params={"$top": 10}
            )
            data = response.json()
            return data.get('value', [])
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error occurred: {str(e)}")
            logger.error(f"Response content: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error retrieving documents: {str(e)}")
            raise
        
    async def get_attachments(self, message_id: str) -> List[Dict[str, Any]]:
        """Retrieve attachments for a specific email.
        
        Args:
            message_id: The ID of the email message.
            
        Returns:
            List of attachment objects with metadata and content.
        """
        logger.info(f"Retrieving attachments for message ID: {message_id}")
        access_token = await self._get_access_token()
        headers = {"Authorization": f"Bearer {access_token}"}
        
        try:
            user_email = get_env_variable('user_email')
            response = await self.client.get(
                f'https://graph.microsoft.com/v1.0/users/{user_email}/messages/{message_id}/attachments',
                headers=headers
            )
            data = response.json()
            return data.get('value', [])
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error occurred: {str(e)}")
            logger.error(f"Response content: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error retrieving attachments: {str(e)}")
            raise

    async def save_to_onedrive(self, file_path: str, file_name: str, folder: str = None) -> Dict[str, Any]:
        """Upload a file to OneDrive using Microsoft Graph API.

        Args:
            file_path: Local path to the file to upload.
            file_name: Name to give the file in OneDrive.
            folder: Optional folder path in OneDrive. If not provided, uses the default from config.

        Returns:
            Dict containing the response from the upload operation.
        """
        logger.info(f"Uploading file {file_name} to OneDrive")
        access_token = await self._get_access_token()
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/octet-stream"
        }

        # Use the folder from config if not provided
        if folder is None:
            folder = config["onedrive"]["emails_folder"]

        try:
            user_email = get_env_variable('user_email')
            with open(file_path, "rb") as file:
                response = await self.client.put(
                    f'https://graph.microsoft.com/v1.0/users/{user_email}/drive/root:/data_PMSA/emails_1/{file_name}:/content',
                    headers=headers,
                    content=file.read()
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error occurred: {str(e)}")
            logger.error(f"Response content: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error uploading file to OneDrive: {str(e)}")
            raise

    async def save_email_content_to_onedrive(self, email_content: str, file_name: str, folder: str = None) -> dict:
        """Upload email content directly to OneDrive as a file."""
        logger.info(f"Uploading email content as {file_name} to OneDrive")
        access_token = await self._get_access_token()
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "text/plain"
        }
        if folder is None:
            folder = config["onedrive"]["emails_folder"]
        user_email = get_env_variable('user_email')
        # Use cloud-based path format
        upload_url = f'https://graph.microsoft.com/v1.0/users/{user_email}/drive/root:/{folder}/{file_name}:/content'
        print(f"Uploading to URL: {upload_url}")
        response = await self.client.put(
            upload_url,
            headers=headers,
            content=email_content.encode("utf-8")
        )
        response.raise_for_status()
        return response.json() 