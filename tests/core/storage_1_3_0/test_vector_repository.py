import pytest
import asyncio
from pathlib import Path
import orjson
from datetime import datetime

from openai import OpenAI
from core.storage_1_3_0.vector_repository import VectorRepository
from core.utils.config import config

@pytest.mark.asyncio
async def test_vector_repository_upload():
    """Test uploading a single document to the vector store."""
    # Create a test vector store first
    client = OpenAI(api_key=config["openai"]["api_key"])
    vector_store = client.vector_stores.create(
        name="test-vector-store"
    )
    
    # Create test data
    test_data = {
        "subject": "Test Email",
        "from_": "test@example.com",
        "to": ["recipient@example.com"],
        "cc": ["cc@example.com"],
        "body": "This is the email body",
        "filename": "test_email.msg",
        "text_content": "This is the full text content of the email for vector storage.",
        "created_at": datetime.now().isoformat(),
        "last_modified": datetime.now().isoformat(),
        "parent_email_id": "12345",
        "tags": ["test", "email"],
        "one_drive_url": "https://onedrive.com/test/12345"
    }

    # Create test directory and file
    test_dir = Path("test_data")
    test_dir.mkdir(exist_ok=True)
    test_file = test_dir / "test_email.json"
    test_file.write_bytes(orjson.dumps(test_data))

    try:
        # Initialize repository with the new vector store ID
        repo = VectorRepository()
        repo.store_id = vector_store.id  # Override the store ID with our test store
        
        # Test single upload
        success = await repo.upload_document(test_file)
        assert success, "Failed to upload single document"

        # Test batch upload
        stats = await repo.batch_upload(test_dir)
        assert stats["success"] > 0, "Failed to process batch upload"
        assert stats["failed"] == 0, "Unexpected failures in batch upload"

    finally:
        # Cleanup
        test_file.unlink()
        test_dir.rmdir()
        # Note: We're not deleting the vector store as the API doesn't support deletion yet

if __name__ == "__main__":
    asyncio.run(test_vector_repository_upload()) 