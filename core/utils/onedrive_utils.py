import os
from typing import List
from core.graph_1_1_0.main import GraphClient
from core.utils.config import app_config

async def list_folder_contents(folder_path: str) -> List[dict]:
    """List all files in a OneDrive folder.
    
    Args:
        folder_path: The path of the folder to list
    """
    try:
        client = GraphClient()
        user_email = app_config.user.email
        url = f"https://graph.microsoft.com/v1.0/users/{user_email}/drive/root:/{folder_path}:/children"
        access_token = await client._get_access_token()
        headers = {"Authorization": f"Bearer {access_token}"}
        response = await client.client.get(url, headers=headers)
        response.raise_for_status()
        return response.json().get("value", [])
    except Exception as e:
        print(f"Error listing folder contents: {str(e)}")
        raise

async def delete_item(client: GraphClient, item_id: str) -> None:
    """Delete an item from OneDrive by its ID."""
    user_email = app_config.user.email
    url = f"https://graph.microsoft.com/v1.0/users/{user_email}/drive/items/{item_id}"
    access_token = await client._get_access_token()
    headers = {"Authorization": f"Bearer {access_token}"}
    response = await client.client.delete(url, headers=headers)
    response.raise_for_status()

async def clear_folder(folder_path: str) -> None:
    """
    Clear all files in a OneDrive folder.
    
    Args:
        folder_path: Path to the folder in OneDrive
        
    Raises:
        Exception: If clearing fails
    """
    try:
        client = GraphClient()
        user_email = app_config.user.email
        
        # Get access token
        access_token = await client._get_access_token()
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Get folder contents
        folder_url = f"https://graph.microsoft.com/v1.0/users/{user_email}/drive/root:/{folder_path}:/children"
        response = await client.client.get(folder_url, headers=headers)
        response.raise_for_status()
        
        # Delete each file
        for item in response.json().get("value", []):
            if item.get("file"):  # Only delete files, not folders
                file_id = item["id"]
                delete_url = f"https://graph.microsoft.com/v1.0/users/{user_email}/drive/items/{file_id}"
                await client.client.delete(delete_url, headers=headers)
                
    except Exception as e:
        raise Exception(f"Failed to clear folder {folder_path}: {str(e)}")

async def load_json_file(file_path: str) -> dict:
    """Load a JSON file from OneDrive and return its contents as a dict.
    Args:
        file_path: Path to the file in OneDrive
    Returns:
        The loaded JSON data as a dict
    Raises:
        Exception if loading or parsing fails
    """
    try:
        client = GraphClient()
        user_email = app_config.user.email
        access_token = await client._get_access_token()
        headers = {"Authorization": f"Bearer {access_token}"}
        # Normalize file path for OneDrive API
        file_path = file_path.replace('\\', '/').strip('/')
        url = f"https://graph.microsoft.com/v1.0/users/{user_email}/drive/root:/{file_path}:/content"
        response = await client.client.get(url, headers=headers)
        response.raise_for_status()
        return response.json() if hasattr(response, 'json') else response.json()
    except Exception as e:
        print(f"Error loading JSON file from OneDrive: {str(e)}")
        raise

async def save_json_file(file_path: str, data: dict) -> None:
    """Save a dict as a JSON file to OneDrive.
    Args:
        file_path: Path to save the file in OneDrive
        data: The dict to save as JSON
    Raises:
        Exception if saving fails
    """
    import json
    try:
        client = GraphClient()
        user_email = app_config.user.email
        # Convert dict to JSON bytes
        content_bytes = json.dumps(data, indent=2).encode('utf-8')
        # Normalize file path for OneDrive API
        file_path = file_path.replace('\\', '/').strip('/')
        await client.upload_file(user_email, file_path, content_bytes)
    except Exception as e:
        print(f"Error saving JSON file to OneDrive: {str(e)}")
        raise

if __name__ == "__main__":
    import asyncio
    
    async def main():
        # Example usage
        folder = app_config.onedrive.processed_emails_folder  # or any other folder path
        await clear_folder(folder)
    
    asyncio.run(main()) 