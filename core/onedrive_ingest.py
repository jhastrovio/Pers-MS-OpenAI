import os
import asyncio
from core.graph_client import MSGraphClient
from core.auth import MSGraphAuth
from core.vectorstore_upload import upload_to_vectorstore
import httpx
from pathlib import Path
from datetime import datetime
import re

# Ingest all files from the PERS-MS-OPENAI root folder and subfolders
TARGET_FOLDERS = [
    "PERS-MS-OPENAI",
]

DOWNLOAD_DIR = Path("downloads_onedrive")
DOWNLOAD_DIR.mkdir(exist_ok=True)

# Set your vector store ID here (reuse this for all uploads)
VECTOR_STORE_ID = os.getenv("OPENAI_VECTOR_STORE_ID") or "vs_abc123..."  # TODO: Replace with your actual vector store ID

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
                    content = await client.get_file_content(file_id, user_email=user_email)
                    # Save as binary or text depending on type
                    mode = "wb" if isinstance(content, bytes) else "w"
                    with open(local_path, mode, encoding=None if mode=="wb" else "utf-8") as f:
                        f.write(content)
                except Exception as e:
                    print(f"[WARN] Failed to download {filename} from OneDrive: {e}")
                    if hasattr(e, 'response') and hasattr(e.response, 'text'):
                        print(f"[DEBUG] Error response: {e.response.text}")
                    continue
                # Upload to OpenAI Vector Store
                match = re.match(r"([A-Za-z0-9_-]+)_(.+)", filename)
                if match:
                    email_id = match.group(1)
                    original_filename = match.group(2)
                else:
                    email_id = None
                    original_filename = filename

                metadata = {
                    "filename": original_filename,
                    "email_id": email_id,
                    "filetype": os.path.splitext(filename)[1].lower(),
                    "onedrive_path": item.get("full_path"),
                    "onedrive_id": item.get("id"),
                    "size": item.get("size"),
                    "uploaded_at": datetime.utcnow().isoformat(),
                }
                try:
                    openai_file_id, _ = upload_to_vectorstore(
                        file_path=str(local_path),
                        attributes=metadata,
                        vector_store_id=VECTOR_STORE_ID
                    )
                    print(f"[UPLOAD] {filename} → OpenAI file_id: {openai_file_id}")
                except Exception as e:
                    print(f"[WARN] Failed to upload {filename} to OpenAI Vector Store: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 