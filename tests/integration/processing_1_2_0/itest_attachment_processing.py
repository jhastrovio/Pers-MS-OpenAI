"""
Integration test for AttachmentProcessor.
Tests processing of email attachments using DocumentProcessor.
"""

import os
import pytest
import asyncio
import tempfile
import json
from datetime import datetime
import uuid

from core.processing_1_2_0.processors.document_processor import DocumentProcessor
from core.processing_1_2_0.processors.attachment_processor import AttachmentProcessor
from core.graph_1_1_0.metadata import EmailDocumentMetadata
from core.utils.config import config, PROCESSING_CONFIG
from core.utils.ms_graph_client import GraphClient

LOG_PATH = "itest_attachment_processing.log"

def log(msg):
    print(msg)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(str(msg) + "\n")

@pytest.mark.asyncio
async def test_attachment_processing_e2e():
    """
    End-to-end integration test for AttachmentProcessor.
    Tests processing of real files from OneDrive as attachments.
    """
    # Clear log at start
    with open(LOG_PATH, "w", encoding="utf-8") as f:
        f.write("")

    # Verify required environment variables
    required_vars = ['CLIENT_ID', 'CLIENT_SECRET', 'TENANT_ID', 'USER_EMAIL']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        log(f"Missing required environment variables: {', '.join(missing_vars)}")
        pytest.skip(f"Missing required environment variables: {', '.join(missing_vars)}")

    # Initialize processors
    doc_processor = DocumentProcessor(PROCESSING_CONFIG)
    attachment_processor = AttachmentProcessor(doc_processor)
    
    # Create a sample parent email metadata
    parent_email = EmailDocumentMetadata(
        document_id=str(uuid.uuid4()),
        type="email",
        filename="sample_email.eml",
        one_drive_url="",
        created_at=datetime.now().isoformat(),
        size=1024,
        content_type="message/rfc822",
        source="email",
        is_attachment=False,
        text_content="Sample email content",
        tags=[],
        from_="sender@example.com",
        subject="Test Email with Attachments"
    )

    user_email = config["user"]["email"]
    docs_folder = PROCESSING_CONFIG["FOLDERS"]["DOCUMENTS"]
    processed_folder = PROCESSING_CONFIG["FOLDERS"]["PROCESSED_DOCUMENTS"]
    allowed_exts = PROCESSING_CONFIG["ALLOWED_EXTENSIONS"]

    log(f"\nConfiguration:")
    log(f"User email: {user_email}")
    log(f"Documents folder: {docs_folder}")
    log(f"Processed folder: {processed_folder}")
    log(f"Allowed extensions: {allowed_exts}")
    log(f"Parent email ID: {parent_email.document_id}")
    log(f"Parent email subject: {parent_email.subject}")

    graph_client = GraphClient()
    log(f"\nListing files in OneDrive folder: {docs_folder}")
    files = await graph_client.list_files_in_folder(docs_folder)
    log(f"Raw files found: {[f['name'] for f in files]}")
    files = [f for f in files if os.path.splitext(f['name'])[1].lower() in allowed_exts]

    log(f"Found {len(files)} valid files in OneDrive folder.")
    if not files:
        log(f"No valid files found in OneDrive folder '{docs_folder}'. Allowed extensions: {allowed_exts}")
        pytest.skip(f"No valid files found in OneDrive folder '{docs_folder}'. Allowed extensions: {allowed_exts}")

    # Process first 10 files as attachments
    print(f"\nProcessing first 10 files as attachments:")
    for i, file in enumerate(files[:10]):
        print(f"\nProcessing file {i+1}/10: {file['name']}")
        
        # Download file
        print(f"Downloading file...")
        try:
            content = await graph_client.download_file_from_onedrive(docs_folder, file['name'])
            if not content:
                print(f"Failed to download file: No content returned")
                continue
            print(f"Downloaded {len(content)} bytes")
            
            try:
                # Process file as attachment
                print(f"Processing with AttachmentProcessor...")
                result = await attachment_processor.process(
                    content=content,
                    filename=file['name'],
                    parent_email_meta=parent_email
                )
                
                # Print metadata
                print("\nGenerated metadata:")
                print(f"Filename: {result['metadata'].filename}")
                print(f"Title: {result['metadata'].title}")
                print(f"Type: {result['metadata'].type}")
                print(f"Is attachment: {result['metadata'].is_attachment}")
                print(f"Parent email ID: {result['metadata'].parent_email_id}")
                print(f"From: {result['metadata'].from_}")
                print(f"Subject: {result['metadata'].subject}")
                print(f"OneDrive URL: {result['metadata'].one_drive_url}")
                print(f"Content type: {result['metadata'].content_type}")
                print(f"Size: {result['metadata'].size} bytes")
                print(f"Text content length: {len(result['metadata'].text_content)} characters")
                
            except Exception as e:
                print(f"Error processing file: {str(e)}")
                import traceback
                print(traceback.format_exc())
                continue
                
        except Exception as e:
            print(f"Error downloading file: {str(e)}")
            import traceback
            print(traceback.format_exc())
            continue

    # Verify results in OneDrive
    print("\nVerifying processed files in OneDrive...")
    processed_files = await graph_client.list_files_in_folder(processed_folder)
    print(f"\nFound {len(processed_files)} files in {processed_folder}:")
    for file in processed_files:
        print(f"- {file['name']}")
    
    log(f"\nProcessed {len(files[:10])} files as attachments.")
    log(f"Results are available in OneDrive folder: {processed_folder}")
    
    # List files in processed folder to verify
    log(f"\nVerifying files in processed folder: {processed_folder}")
    processed_files = await graph_client.list_files_in_folder(processed_folder)
    log(f"Files found in processed folder: {[f['name'] for f in processed_files]}")
    # No assertions: manual review only 

@pytest.mark.asyncio
async def test_attachment_processing_blending():
    """
    Integration test for AttachmentProcessor with JSON blending.
    Downloads an attachment and its paired JSON, processes, and checks blended metadata.
    Only processes files that have a matching .json file.
    """
    # Clear log at start
    with open(LOG_PATH, "w", encoding="utf-8") as f:
        f.write("")

    required_vars = ['CLIENT_ID', 'CLIENT_SECRET', 'TENANT_ID', 'USER_EMAIL']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        log(f"Missing required environment variables: {', '.join(missing_vars)}")
        pytest.skip(f"Missing required environment variables: {', '.join(missing_vars)}")

    doc_processor = DocumentProcessor(PROCESSING_CONFIG)
    attachment_processor = AttachmentProcessor(doc_processor)
    attachments_folder = PROCESSING_CONFIG["FOLDERS"]["ATTACHMENTS"]
    allowed_exts = PROCESSING_CONFIG["ALLOWED_EXTENSIONS"]

    graph_client = GraphClient()
    log(f"\nListing files in OneDrive folder: {attachments_folder}")
    files = await graph_client.list_files_in_folder(attachments_folder)
    all_filenames = set(f['name'] for f in files)
    log(f"All files in folder: {sorted(all_filenames)}")

    # Only consider files with allowed extensions and a matching .json file
    candidate_files = []
    for f in files:
        name = f['name']
        ext = os.path.splitext(name)[1].lower()
        json_name = name + ".json"
        if ext in allowed_exts and json_name in all_filenames:
            candidate_files.append(name)
    log(f"Candidate files with matching .json: {candidate_files}")

    if not candidate_files:
        log(f"No valid attachment+json pairs found in '{attachments_folder}'.")
        pytest.skip(f"No valid attachment+json pairs found in '{attachments_folder}'.")

    # Use up to the first 10 valid pairs
    for filename in candidate_files[:10]:
        json_filename = filename + ".json"

        # Download attachment and paired JSON
        content = await graph_client.download_file_from_onedrive(attachments_folder, filename)
        json_content = await graph_client.download_file_from_onedrive(attachments_folder, json_filename)
        if not content or not json_content:
            log(f"Could not download both attachment and paired JSON for {filename}")
            continue

        # Save both to temp files
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, filename)
            json_path = file_path + ".json"
            with open(file_path, "wb") as f:
                f.write(content)
            with open(json_path, "wb") as f:
                f.write(json_content)

            # Process the attachment (will auto-blend with JSON)
            result = await attachment_processor.process(file_path=file_path, filename=filename)

            # Load the JSON for comparison
            with open(json_path, "r", encoding="utf-8") as f:
                json_fields = json.load(f)

            # Check that only allowed fields are blended
            for field in [
                "parent_email_id", "parent_document_id", "message_id", "subject",
                "to", "cc", "date", "title", "author"
            ]:
                if field in json_fields:
                    assert result["metadata"][field] == json_fields[field]
            # Core document fields should not be overwritten
            assert result["metadata"]["filename"] == filename
            assert result["metadata"]["is_attachment"] is True
            assert result["metadata"]["type"] == "attachment"

            log(f"Processed attachment: {filename}")
            log(f"Blended metadata: {result['metadata']}") 