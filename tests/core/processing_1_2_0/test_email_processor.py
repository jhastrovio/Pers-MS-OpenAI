"""
Tests for the EmailProcessor class using real .eml files from OneDrive.
"""

import asyncio
import os
import pytest
import json
from core.graph_1_1_0.main import GraphClient
from core.processing_1_2_0.processors.email_processor import EmailProcessor
from core.utils.config import app_config
from core.utils.filename_utils import create_hybrid_filename
from httpx import HTTPStatusError
from datetime import datetime
from core.utils.onedrive_utils import list_folder_contents
from core.utils.ms_graph_client import GraphClient as MsGraphClient

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
    client = GraphClient()
    
    try:
        # Get a real message from OneDrive
        user_email = app_config.user.email
        
        # List files in the emails_1 folder to find .eml files
        emails_folder = app_config.onedrive.emails_folder  # data_PMSA/emails_1
        files = await list_folder_contents(emails_folder)
        
        # Find the first .eml file
        eml_file = next((f for f in files if f["name"].endswith(".eml")), None)
        if not eml_file:
            pytest.skip("No .eml files found in OneDrive folder: " + emails_folder)
        
        # Download the .eml file bytes
        ms_client = MsGraphClient()
        eml_bytes = await ms_client.download_file_from_onedrive(emails_folder, eml_file["name"])
        
        # Process the email
        result = await processor.process(eml_bytes, user_email)
        
        # Verify the email processing result structure
        assert "subject" in result
        assert "body" in result
        assert "filename" in result
        assert "metadata" in result
        
        # Verify metadata
        metadata = result["metadata"]
        assert "document_id" in metadata
        assert metadata["type"] == "email"
        assert "filename" in metadata
        assert "one_drive_url" in metadata
        assert "outlook_url" in metadata
        assert "created_at" in metadata
        assert "size" in metadata
        assert metadata["content_type"] == "message/rfc822"
        assert metadata["source"] == "email"
        assert metadata["is_attachment"] == False
        assert "message_id" in metadata
        assert "subject" in metadata
        assert "from_" in metadata
        assert "to" in metadata
        assert "cc" in metadata
        assert "date" in metadata
        assert "text_content" in metadata
        assert "attachments" in metadata
        assert "tags" in metadata
        
        # Verify content
        assert isinstance(result["body"], str)
        assert len(result["body"]) > 0
        
        # Verify filename format
        assert result["filename"].endswith(".json")
        assert "_" in result["filename"]
        assert metadata["document_id"] in result["filename"]
        
        # Verify the processed file exists in OneDrive
        processed_folder = app_config.onedrive.processed_emails_folder  # data_PMSA/processed_emails_2
        processed_path = f"{processed_folder}/{result['filename']}"
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
    client = GraphClient()
    
    try:
        # Get a real message from OneDrive
        user_email = app_config.user.email
        
        # List files in the emails_1 folder to find .eml files
        emails_folder = app_config.onedrive.emails_folder  # data_PMSA/emails_1
        files = await list_folder_contents(emails_folder)
        
        # Find the first .eml file
        eml_file = next((f for f in files if f["name"].endswith(".eml")), None)
        if not eml_file:
            pytest.skip("No .eml files found in OneDrive folder: " + emails_folder)
        
        # Download the .eml file bytes
        ms_client = MsGraphClient()
        eml_bytes = await ms_client.download_file_from_onedrive(emails_folder, eml_file["name"])
        
        # Process the email
        result = await processor.process(eml_bytes, user_email)
        
        # Verify the email processing
        assert "subject" in result
        assert "body" in result
        assert "filename" in result
        assert "metadata" in result
        
        # Verify metadata fields
        metadata = result["metadata"]
        assert metadata["type"] == "email"
        assert metadata["source"] == "email"
        assert metadata["is_attachment"] == False
        assert isinstance(metadata["to"], list)
        assert isinstance(metadata["cc"], list)
        assert isinstance(metadata["attachments"], list)
        assert isinstance(metadata["tags"], list)
        
        # Verify text content
        assert isinstance(metadata["text_content"], str)
        assert len(metadata["text_content"]) > 0
        
        # Verify the processed file exists in OneDrive
        processed_folder = app_config.onedrive.processed_emails_folder  # data_PMSA/processed_emails_2
        processed_path = f"{processed_folder}/{result['filename']}"
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
    client = GraphClient()
    
    try:
        # Get a real message from OneDrive
        user_email = app_config.user.email
        
        # List files in the emails_1 folder to find .eml files
        emails_folder = app_config.onedrive.emails_folder  # data_PMSA/emails_1
        files = await list_folder_contents(emails_folder)
        
        # Find the first .eml file
        eml_file = next((f for f in files if f["name"].endswith(".eml")), None)
        if not eml_file:
            pytest.skip("No .eml files found in OneDrive folder: " + emails_folder)
        
        # Download the .eml file bytes
        ms_client = MsGraphClient()
        eml_bytes = await ms_client.download_file_from_onedrive(emails_folder, eml_file["name"])
        
        # Process the email
        result = await processor.process(eml_bytes, user_email)
        
        # Verify filename format
        assert result["filename"].endswith(".json")
        assert "_" in result["filename"]
        assert result["metadata"]["document_id"] in result["filename"]
        
        # Verify the processed file exists in OneDrive
        processed_folder = app_config.onedrive.processed_emails_folder  # data_PMSA/processed_emails_2
        processed_path = f"{processed_folder}/{result['filename']}"
        file_exists = await client.file_exists(processed_path)
        assert file_exists, f"Processed file not found at {processed_path}"
        
    except Exception as e:
        pytest.fail(f"Filename generation test failed: {str(e)}")
    finally:
        await processor.close()

if __name__ == "__main__":
    pytest.main([__file__]) 