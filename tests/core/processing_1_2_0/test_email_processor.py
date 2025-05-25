"""
Tests for EmailProcessor using real .eml files from OneDrive.
"""

import asyncio
import os
import pytest
import json
from core.graph_1_1_0.main import GraphClient  # Use the consolidated GraphClient
from core.processing_1_2_0.processors.email_processor import EmailProcessor
from core.utils.config import config
from core.utils.filename_utils import create_hybrid_filename
from httpx import HTTPStatusError
from datetime import datetime
from core.utils.onedrive_utils import list_folder_contents
from core.utils.logging import configure_logging, get_logger

@pytest.fixture
def email_processor():
    """Create an EmailProcessor instance for testing."""
    return EmailProcessor(config)

@pytest.mark.asyncio
async def test_email_processing_workflow():
    """Test the full email processing workflow using real .eml files:
    1. Get message metadata and web URL
    2. Process email content
    3. Save metadata
    """
    processor = EmailProcessor(config)
    async with GraphClient() as client:
        try:
            # Get a real message from OneDrive
            user_email = config["user"]["email"]
            
            # List files in the emails_1 folder to find .eml files
            emails_folder = config["onedrive"]["emails_folder"]  # data_PMSA/emails_1
            files = await list_folder_contents(emails_folder)
            
            # Find the first .eml file
            eml_file = next((f for f in files if f["name"].endswith(".eml")), None)
            if not eml_file:
                pytest.skip("No .eml files found in OneDrive folder: " + emails_folder)
            
            # Download the .eml file bytes
            eml_bytes = await client.download_file_from_onedrive(emails_folder, eml_file["name"])
            
            # Process the email
            result = await processor.process(eml_bytes, user_email)
            
            # Verify the email processing result structure
            assert "email_id" in result
            assert "metadata" in result
            
            # Verify metadata
            metadata = result["metadata"]
            assert "document_id" in metadata
            assert metadata["type"] == "email"
            assert "filename" in metadata
            assert "source_url" in metadata
            assert "is_attachment" in metadata
            assert "message_id" in metadata
            assert "subject" in metadata
            assert "from_" in metadata
            assert "recipients" in metadata
            assert "date" in metadata
            assert "text_content" in metadata
            assert "attachments" in metadata
            
            # Verify the processed file exists in OneDrive
            processed_folder = config["onedrive"]["processed_emails_folder"]  # data_PMSA/processed_emails_2
            processed_path = f"{processed_folder}/{metadata['filename']}"
            file_exists = await client.file_exists(processed_path)
            assert file_exists, f"Processed file not found at {processed_path}"
            
        except Exception as e:
            pytest.fail(f"Email processing workflow test failed: {str(e)}")
        finally:
            await processor.close()

@pytest.mark.asyncio
async def test_email_with_metadata():
    """Test processing an email with complete metadata using a real .eml file."""
    processor = EmailProcessor(config)
    async with GraphClient() as client:
        try:
            # Get a real message from OneDrive
            user_email = config["user"]["email"]
            
            # List files in the emails_1 folder to find .eml files
            emails_folder = config["onedrive"]["emails_folder"]  # data_PMSA/emails_1
            files = await list_folder_contents(emails_folder)
            
            # Find the first .eml file
            eml_file = next((f for f in files if f["name"].endswith(".eml")), None)
            if not eml_file:
                pytest.skip("No .eml files found in OneDrive folder: " + emails_folder)
            
            # Download the .eml file bytes
            eml_bytes = await client.download_file_from_onedrive(emails_folder, eml_file["name"])
            
            # Process the email
            result = await processor.process(eml_bytes, user_email)
            
            # Verify the email processing
            assert "email_id" in result
            assert "metadata" in result
            
            # Verify metadata fields
            metadata = result["metadata"]
            assert metadata["type"] == "email"
            assert metadata["is_attachment"] == False
            assert isinstance(metadata["recipients"], list)
            assert isinstance(metadata["attachments"], list)
            
            # Verify text content
            assert isinstance(metadata["text_content"], str)
            
            # Verify the processed file exists in OneDrive
            processed_folder = config["onedrive"]["processed_emails_folder"]  # data_PMSA/processed_emails_2
            processed_path = f"{processed_folder}/{metadata['filename']}"
            file_exists = await client.file_exists(processed_path)
            assert file_exists, f"Processed file not found at {processed_path}"
            
        except Exception as e:
            pytest.fail(f"Metadata test failed: {str(e)}")
        finally:
            await processor.close()

@pytest.mark.asyncio
async def test_filename_generation():
    """Test that filenames are generated correctly for real emails."""
    processor = EmailProcessor(config)
    async with GraphClient() as client:
        try:
            # Get a real message from OneDrive
            user_email = config["user"]["email"]
            
            # List files in the emails_1 folder to find .eml files
            emails_folder = config["onedrive"]["emails_folder"]  # data_PMSA/emails_1
            files = await list_folder_contents(emails_folder)
            
            # Find the first .eml file
            eml_file = next((f for f in files if f["name"].endswith(".eml")), None)
            if not eml_file:
                pytest.skip("No .eml files found in OneDrive folder: " + emails_folder)
            
            # Download the .eml file bytes
            eml_bytes = await client.download_file_from_onedrive(emails_folder, eml_file["name"])
            
            # Process the email
            result = await processor.process(eml_bytes, user_email)
            
            # Verify filename format
            metadata = result["metadata"]
            assert metadata["filename"].endswith(".json")
            assert "_" in metadata["filename"]
            assert metadata["document_id"] in metadata["filename"]
            
            # Verify the processed file exists in OneDrive
            processed_folder = config["onedrive"]["processed_emails_folder"]  # data_PMSA/processed_emails_2
            processed_path = f"{processed_folder}/{metadata['filename']}"
            file_exists = await client.file_exists(processed_path)
            assert file_exists, f"Processed file not found at {processed_path}"

        except Exception as e:
            pytest.fail(f"Filename generation test failed: {str(e)}")
        finally:
            await processor.close()

if __name__ == "__main__":
    pytest.main([__file__]) 