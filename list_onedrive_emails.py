import asyncio
import os
from core.graph_1_1_0.main import GraphClient
from core.utils.config import config

async def list_emails_folder():
    client = GraphClient()
    user_email = os.getenv("USER_EMAIL")
    folder = config["onedrive"]["emails_folder"]
    access_token = await client._get_access_token()
    headers = {"Authorization": f"Bearer {access_token}"}
    url = f"https://graph.microsoft.com/v1.0/users/{user_email}/drive/root:/{folder}:/children"
    response = await client.client.get(url, headers=headers)
    response.raise_for_status()
    items = response.json().get("value", [])
    print(f"Files in {folder}:")
    for item in items:
        print("-", item["name"])

if __name__ == "__main__":
    asyncio.run(list_emails_folder()) 