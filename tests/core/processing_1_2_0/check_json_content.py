import asyncio
import json
from core.graph_1_1_0.main import GraphClient
from core.utils.config import app_config
import os

async def check_json_content():
    """Download and check the content of a processed JSON file."""
    client = GraphClient()
    
    # Get user email from config
    user_email = app_config.user.email
    
    # Get the first JSON file from the processed_emails_2 folder
    folder = app_config.onedrive.processed_emails_folder
    url = f"https://graph.microsoft.com/v1.0/users/{user_email}/drive/root:/{folder}:/children"
    access_token = await client._get_access_token()
    headers = {"Authorization": f"Bearer {access_token}"}
    response = await client.client.get(url, headers=headers)
    response.raise_for_status()
    files = response.json().get("value", [])
    
    if not files:
        print("No files found in the processed_emails_2 folder")
        return
        
    # Get the first JSON file
    json_file = next((f for f in files if f["name"].endswith(".json")), None)
    if not json_file:
        print("No JSON files found")
        return
        
    # Download the file content with redirect following
    content_url = f"https://graph.microsoft.com/v1.0/users/{user_email}/drive/items/{json_file['id']}/content"
    content_response = await client.client.get(content_url, headers=headers, follow_redirects=True)
    content_response.raise_for_status()
    
    # Parse and print the content
    content = json.loads(content_response.text)
    print("\nFile:", json_file["name"])
    print("\nSubject:", content.get("subject", ""))
    print("\nFrom:", content.get("from", ""))
    print("\nText content preview:", content.get("text_content", "")[:200] + "...")

if __name__ == "__main__":
    asyncio.run(check_json_content()) 