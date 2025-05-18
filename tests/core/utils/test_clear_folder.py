"""
Test utility for clearing OneDrive data folders.
"""

import asyncio
import sys
from core.utils.onedrive_utils import clear_folder
from core.utils.config import config
from typing import List, Optional

async def clear_data_folders(folders: Optional[List[str]] = None):
    """
    Clear specified OneDrive data folders or all data folders if none specified.
    
    Args:
        folders: Optional list of specific folders to clear. If None, clears all data folders.
    """
    # Define all data folders
    data_folders = {
        "emails": config["onedrive"]["emails_folder"],
        "documents": config["onedrive"]["documents_folder"],
        "processed_emails": config["onedrive"]["processed_emails_folder"],
        "processed_documents": config["onedrive"]["processed_documents_folder"],
        "processed_chunks": config["onedrive"]["processed_chunk_dir"],
        "embeddings": config["onedrive"]["embeddings_dir"]
    }
    
    # If specific folders are requested, filter the data_folders
    if folders:
        folders = [f.lower() for f in folders]
        folders_to_clear = {k: v for k, v in data_folders.items() if k.lower() in folders}
        if not folders_to_clear:
            print(f"\nWarning: No valid folders found in {folders}")
            print("Available folders:", ", ".join(data_folders.keys()))
            return
    else:
        folders_to_clear = data_folders
    
    # Clear each folder
    success_count = 0
    error_count = 0
    
    for folder_name, folder_path in folders_to_clear.items():
        try:
            await clear_folder(folder_path)
            print(f"Cleared: {folder_name}")
            success_count += 1
        except Exception as e:
            print(f"Error: {folder_name} - {str(e)}")
            error_count += 1
    
    print(f"\nCompleted: {success_count} cleared, {error_count} failed")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        folders = sys.argv[1:]
        asyncio.run(clear_data_folders(folders))
    else:
        asyncio.run(clear_data_folders()) 