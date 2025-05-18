import os
from typing import List
from core.graph_1_1_0.main import GraphClient
from core.utils.config import config

async def list_folder_contents(folder_path: str) -> List[dict]:
    """List all files in a OneDrive folder.
    
    Args:
        folder_path: The path of the folder to list
    """
    try:
        client = GraphClient()
        user_email = config["user"]["email"]
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
    user_email = config["user"]["email"]
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
        user_email = config["user"]["email"]
        
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

if __name__ == "__main__":
    import asyncio
    
    async def main():
        # Example usage
        folder = config["onedrive"]["processed_emails_folder"]  # or any other folder path
        await clear_folder(folder)
    
    asyncio.run(main()) 