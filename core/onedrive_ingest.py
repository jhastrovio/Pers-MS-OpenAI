import os
import asyncio
from core.graph_client import MSGraphClient
from core.auth import MSGraphAuth
from core.openai_service import openai_service
import httpx
from pathlib import Path
from datetime import datetime

# Ingest all files from the PERS-MS-OPENAI root folder and subfolders
TARGET_FOLDERS = [
    "PERS-MS-OPENAI",
]

DOWNLOAD_DIR = Path("downloads_onedrive")
DOWNLOAD_DIR.mkdir(exist_ok=True)

async def main():
    user_email = os.environ.get("USER_EMAIL")
    if not user_email:
        raise ValueError("USER_EMAIL environment variable not set.")
    auth = MSGraphAuth(
        client_id=os.environ["CLIENT_ID"],
        client_secret=os.environ["CLIENT_SECRET"],
        tenant_id=os.environ["TENANT_ID"]
    )
    client = MSGraphClient(auth=auth)
    for folder in TARGET_FOLDERS:
        print(f"[INFO] Ingesting OneDrive folder: {folder}")
        items = await client.fetch_drive_items(user_email, folder_path=folder, recursive=True)
        for item in items:
            if "file" in item:
                print(f"[FILE] {item['full_path']}")
                # Download file locally
                file_id = item["id"]
                filename = item["name"]
                local_path = DOWNLOAD_DIR / filename
                # Download file content from OneDrive
                try:
                    content = await client.get_file_content(file_id)
                    # Save as binary or text depending on type
                    mode = "wb" if isinstance(content, bytes) else "w"
                    with open(local_path, mode, encoding=None if mode=="wb" else "utf-8") as f:
                        f.write(content)
                except Exception as e:
                    print(f"[WARN] Failed to download {filename} from OneDrive: {e}")
                    continue
                # Upload to OpenAI File Search
                metadata = {
                    "filename": filename,
                    "filetype": os.path.splitext(filename)[1].lower(),
                    "onedrive_path": item.get("full_path"),
                    "onedrive_id": item.get("id"),
                    "size": item.get("size"),
                    "uploaded_at": datetime.utcnow().isoformat(),
                }
                try:
                    openai_file_id = await openai_service.upload_file_to_file_search(str(local_path), metadata=metadata)
                    print(f"[UPLOAD] {filename} → OpenAI file_id: {openai_file_id}")
                except Exception as e:
                    print(f"[WARN] Failed to upload {filename} to OpenAI File Search: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 