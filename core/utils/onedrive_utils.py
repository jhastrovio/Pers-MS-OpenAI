import os
from typing import List
from core.graph_1_1_0.main import GraphClient
from core.utils.config import config

async def list_folder_contents(client: GraphClient, folder_path: str) -> List[dict]:
    """List all items in a OneDrive folder."""
    user_email = os.getenv("USER_EMAIL")
    url = f"https://graph.microsoft.com/v1.0/users/{user_email}/drive/root:/{folder_path}:/children"
    access_token = await client._get_access_token()
    headers = {"Authorization": f"Bearer {access_token}"}
    response = await client.client.get(url, headers=headers)
    response.raise_for_status()
    return response.json().get("value", [])

async def delete_item(client: GraphClient, item_id: str) -> None:
    """Delete an item from OneDrive by its ID."""
    user_email = os.getenv("USER_EMAIL")
    url = f"https://graph.microsoft.com/v1.0/users/{user_email}/drive/items/{item_id}"
    access_token = await client._get_access_token()
    headers = {"Authorization": f"Bearer {access_token}"}
    response = await client.client.delete(url, headers=headers)
    response.raise_for_status()

async def clear_folder(folder_path: str) -> None:
    """Delete all contents of a specified OneDrive folder."""
    client = GraphClient()
    try:
        # List all items in the folder
        items = await list_folder_contents(client, folder_path)
        print(f"Found {len(items)} items in {folder_path}")
        
        # Delete each item
        for item in items:
            try:
                await delete_item(client, item["id"])
                print(f"Deleted: {item['name']}")
            except Exception as e:
                print(f"Error deleting {item['name']}: {str(e)}")
                continue
        
        print(f"Successfully cleared folder: {folder_path}")
        
    except Exception as e:
        print(f"Error clearing folder: {str(e)}")
        raise

if __name__ == "__main__":
    import asyncio
    
    async def main():
        # Example usage
        folder = config["onedrive"]["processed_emails_folder"]  # or any other folder path
        await clear_folder(folder)
    
    asyncio.run(main()) 