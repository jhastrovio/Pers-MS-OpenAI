from pathlib import Path
from typing import Any, Dict, List, Optional
import asyncio
import logging
import os

import orjson
from openai import OpenAI
from openai.types.file_object import FileObject

from core.utils.config import config
from core.utils.onedrive_utils import list_folder_contents
from core.utils.ms_graph_client import GraphClient

logger = logging.getLogger(__name__)

# Fields to copy directly from metadata to attributes
KEEP = ["subject", "from_", "body", "filename"]

class VectorRepository:
    def __init__(
        self,
        api_key: Optional[str] = None,
        max_retries: int = 3
    ):
        """Initialize the vector store repository."""
        self.client = OpenAI(
            api_key=api_key or config["openai"]["api_key"]
        )
        self.store_id = config["openai"]["vector_store_id"]
        self.max_retries = max_retries
        self.graph_client = GraphClient()
        logger.info(f"Initialized vector store repository with store ID: {self.store_id}")

   def _build_attrs(self, meta: Dict[str, Any]) -> Dict[str, str]:
    """Build attributes from metadata for vector store."""
    attrs: Dict[str, str] = {}

    # --- your existing logic here ---
    for k in KEEP:
        if v := meta.get(k):
            attrs[k.replace("from_", "from")] = str(v)[:512]

    if recipients := meta.get("to", []) + meta.get("cc", []):
        attrs["recipients"] = ",".join(str(r) for r in recipients)[:512]

    if meta.get("last_modified") and meta.get("created_at"):
        attrs["dates"] = orjson.dumps({
            "c": meta["created_at"][:19],
            "m": meta["last_modified"][:19]
        }).decode()

    if parent_id := meta.get("parent_email_id"):
        attrs["rel"] = str(parent_id)

    if tags := meta.get("tags"):
        attrs["tags"] = ",".join(str(t) for t in tags)[:512]

    if one_drive_url := meta.get("one_drive_url", ""):
        attrs["source_id"] = one_drive_url.rpartition("/")[-1]

    attrs["version"] = "v1"

    # --- new extension logic ---
    filename = meta.get("filename", "")
    if "." in filename:
        ext = filename.rsplit(".", 1)[1].lower()
        attrs["extension"] = f".{ext}"  # e.g. ".xls" or ".xlsx"
    else:
        attrs["extension"] = ""

    return attrs

    def _extract_text_content(self, meta: Dict[str, Any]) -> str:
        """Extract text content from metadata, handling different possible field names."""
        # Check common field names for text content
        for field in ["text_content", "body", "content", "text", "email_text"]:
            if content := meta.get(field):
                return content
                
        # If we can't find text content in expected fields, use the entire metadata as text
        # This is a fallback to ensure we always have something to upload
        return orjson.dumps(meta).decode('utf-8')

    async def upload_document(self, file_info: Dict[str, Any]) -> bool:
        """Upload a single document and its metadata to the vector store."""
        try:
            user_email = config["user"]["email"]
            folder_path = file_info["parentReference"]["path"].split("root:")[-1].strip("/")
            file_name = file_info["name"]
            
            # Download the file content
            logger.info(f"Downloading {file_name} from {folder_path}")
            content = await self.graph_client.download_file_from_onedrive(folder_path, file_name)
            
            if not content:
                logger.error(f"Failed to download file from OneDrive: {file_name}")
                return False
            
            # Parse JSON content
            try:
                meta = orjson.loads(content)
                # Log a sample of the metadata to help diagnose issues
                logger.info(f"Metadata keys in {file_name}: {list(meta.keys())[:5]}...")
            except Exception as e:
                logger.error(f"Failed to parse JSON content from {file_name}: {e}")
                return False
            
            # Extract text content using our helper method
            text_content = self._extract_text_content(meta)
            if not text_content:
                logger.error(f"No text content found in {file_name} after trying multiple fields")
                return False

            logger.info(f"Uploading to vector store {self.store_id}")
            
            # Create file in OpenAI and upload to vector store
            file: FileObject = self.client.files.create(
                file=(os.path.splitext(file_name)[0] + ".txt", text_content, "text/plain"),
                purpose="assistants"
            )

            self.client.vector_stores.files.create(
                self.store_id,
                file_id=file.id,
                attributes=self._build_attrs(meta)
            )

            logger.info(f"Successfully uploaded {file_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to upload {file_info.get('name', 'unknown')}: {e}")
            return False

    async def batch_upload(self, directory: str, batch_size: int = 10, file_filter: Optional[callable] = None) -> Dict[str, int]:
        """Upload multiple documents in batches from OneDrive.
        
        Args:
            directory: OneDrive directory path containing the files
            batch_size: Number of files to process in each batch
            file_filter: Optional function to filter which files to process
        """
        stats = {"success": 0, "failed": 0}
        
        try:
            # List files in the OneDrive directory
            files = await list_folder_contents(directory)
            json_files = [f for f in files if f["name"].endswith(".json")]
            
            # Apply file filter if provided
            if file_filter:
                json_files = [f for f in json_files if file_filter(f)]
            
            total_batches = (len(json_files) + batch_size - 1) // batch_size
            logger.info(f"Starting batch upload of {len(json_files)} files to vector store {self.store_id}")
            
            for i in range(0, len(json_files), batch_size):
                batch = json_files[i:i + batch_size]
                results = await asyncio.gather(
                    *(self.upload_document(f) for f in batch),
                    return_exceptions=True
                )
                
                stats["success"] += sum(1 for r in results if r is True)
                stats["failed"] += sum(1 for r in results if r is False or isinstance(r, Exception))
                
                logger.info(f"Processed batch {i//batch_size + 1}/{total_batches}: {stats}")
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to process batch upload: {e}")
            return stats

async def main():
    """Main entry point for vector store operations."""
    logging.basicConfig(level=logging.INFO)
    
    repo = VectorRepository()
    directory = config["onedrive"]["processed_emails_folder"]
    
    stats = await repo.batch_upload(directory)
    logger.info(f"Final stats: {stats}")

if __name__ == "__main__":
    asyncio.run(main())
