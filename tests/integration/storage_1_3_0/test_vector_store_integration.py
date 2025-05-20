import pytest
import asyncio
import logging
from core.storage_1_3_0.vector_repository import VectorRepository
from core.utils.config import config
from core.utils.onedrive_utils import list_folder_contents

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@pytest.mark.asyncio
@pytest.mark.integration
async def test_vector_store_integration():
    """Integration test for uploading real processed documents to vector store.
    
    This test processes a limited number of files (20) to verify the upload functionality
    without processing the entire dataset. In production, you would want to:
    1. Track which files have been processed
    2. Only process new or modified files
    3. Handle duplicates appropriately
    """
    # Get the processed documents directory from config
    processed_docs_folder = config["onedrive"]["processed_documents_folder"]
    
    # List files in the OneDrive folder
    files = await list_folder_contents(processed_docs_folder)
    json_files = [f for f in files if f["name"].endswith(".json")]
    
    # Limit to 20 files for testing
    test_files = json_files[:20]
    test_file_names = {f["name"] for f in test_files}
    total_files = len(test_files)
    
    assert total_files > 0, f"No JSON files found in OneDrive folder: {processed_docs_folder}"
    logger.info(f"Testing with {total_files} JSON files from {processed_docs_folder}")

    # Initialize repository
    repo = VectorRepository()
    
    # Upload in batches of 5
    stats = await repo.batch_upload(processed_docs_folder, batch_size=5, file_filter=lambda f: f["name"] in test_file_names)
    
    # Verify results
    assert stats["success"] > 0, "No files were uploaded successfully"
    success_rate = (stats["success"] / total_files) * 100
    
    logger.info(f"Upload complete. Success rate: {success_rate:.1f}%")
    logger.info(f"Successful uploads: {stats['success']}")
    logger.info(f"Failed uploads: {stats['failed']}")
    
    # Assert reasonable success rate (adjust threshold as needed)
    assert success_rate > 80, f"Success rate too low: {success_rate:.1f}%"

if __name__ == "__main__":
    asyncio.run(test_vector_store_integration()) 