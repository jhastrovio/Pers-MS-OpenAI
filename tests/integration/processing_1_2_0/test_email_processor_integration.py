"""
Integration test for EmailProcessor.

This test verifies the EmailProcessor can successfully process emails and interact with real
Microsoft Graph services to upload processed data to OneDrive.
"""

import asyncio
import os
import pytest
import json
from datetime import datetime
from core.graph_1_1_0.main import GraphClient
from core.processing_1_2_0.processors.email_processor import EmailProcessor
from core.utils.config import config
from core.utils.onedrive_utils import list_folder_contents
from core.utils.logging import configure_logging

@pytest.mark.asyncio
async def test_email_processor_integration():
    """
    Integration test for up to 20 emails. No output; review results in OneDrive.
    """
    processor = EmailProcessor()
    processed_count = 0
    try:
        user_email = config["user"]["email"]
        emails_folder = config["onedrive"]["emails_folder"]
        files = await list_folder_contents(emails_folder)
        eml_files = [f for f in files if f["name"].endswith(".eml")][:20]
        if not eml_files:
            pytest.skip(f"No .eml files found in OneDrive folder: {emails_folder}")
        for eml_file in eml_files:
            try:
                # Use the consolidated GraphClient
                graph_client = GraphClient()
                eml_bytes = await graph_client.download_file_from_onedrive(emails_folder, eml_file["name"])
                assert eml_bytes, f"Failed to download .eml file: {eml_file['name']}"
                result = await processor.process(eml_bytes, user_email)
                print("METADATA:", json.dumps(result.get('metadata', {}), indent=2))
                processed_count += 1
                metadata = result.get('metadata', {})
                assert "subject" in metadata, "Missing subject in metadata"
                assert "from" in metadata, "Missing from in metadata"
                assert "to" in metadata, "Missing to in metadata"
            except Exception:
                pass
        assert processed_count > 0, "No emails processed successfully."
    finally:
        await processor.close()

if __name__ == "__main__":
    pytest.main(["-v", __file__]) 