import os
import pytest
import asyncio
import tempfile
from core.processing_1_2_0.processors.document_processor import DocumentProcessor
from core.utils.config import app_config, PROCESSING_CONFIG
from core.utils.ms_graph_client import GraphClient

LOG_PATH = "itest_document_processing.log"

def log(msg):
    print(msg)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(str(msg) + "\n")

@pytest.mark.asyncio
async def test_document_processing_e2e():
    """
    End-to-end integration test for DocumentProcessor.
    Fetches files from OneDrive documents folder, downloads to temp files, processes, and prints metadata for manual review.
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

    processor = DocumentProcessor(PROCESSING_CONFIG)
    user_email = app_config.user.email
    docs_folder = PROCESSING_CONFIG["FOLDERS"]["DOCUMENTS"]
    processed_folder = PROCESSING_CONFIG["FOLDERS"]["PROCESSED_DOCUMENTS"]
    allowed_exts = PROCESSING_CONFIG["ALLOWED_EXTENSIONS"]

    log(f"\nConfiguration:")
    log(f"User email: {user_email}")
    log(f"Documents folder: {docs_folder}")
    log(f"Processed folder: {processed_folder}")
    log(f"Allowed extensions: {allowed_exts}")

    graph_client = GraphClient()
    log(f"\nListing files in OneDrive folder: {docs_folder}")
    files = await graph_client.list_files_in_folder(docs_folder)
    log(f"Raw files found: {[f['name'] for f in files]}")
    files = [f for f in files if os.path.splitext(f['name'])[1].lower() in allowed_exts]

    log(f"Found {len(files)} valid files in OneDrive folder.")
    if not files:
        log(f"No valid files found in OneDrive folder '{docs_folder}'. Allowed extensions: {allowed_exts}")
        pytest.skip(f"No valid files found in OneDrive folder '{docs_folder}'. Allowed extensions: {allowed_exts}")

    # Process first 10 files for debugging
    print(f"\nProcessing first 10 files:")
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
            
            # Save to temp file
            temp_file = f"temp_{file['name']}"
            with open(temp_file, 'wb') as f:
                f.write(content)
            print(f"Saved to temporary file: {temp_file}")
            
            try:
                # Process file
                print(f"Processing with DocumentProcessor...")
                result = await processor.process({
                    "file_path": temp_file,
                    "onedrive_path": f"{docs_folder}/{file['name']}"
                })
                
                # Print metadata
                print("\nGenerated metadata:")
                print(f"Filename: {result['metadata'].filename}")
                print(f"Title: {result['metadata'].title}")
                print(f"Original filename: {file['name']}")
                print(f"OneDrive URL: {result['metadata'].one_drive_url}")
                print(f"Content type: {result['metadata'].content_type}")
                print(f"Size: {result['metadata'].size} bytes")
                print(f"Text content length: {len(result['metadata'].text_content)} characters")
                
                # Log the metadata to file for verification
                log(f"\nProcessed file {i+1}: {file['name']}")
                log(f"OneDrive URL: {result['metadata'].one_drive_url}")
                log(f"Metadata filename: {result['metadata'].filename}")
                
            except Exception as e:
                print(f"Error processing file: {str(e)}")
                import traceback
                print(traceback.format_exc())
            finally:
                # Clean up temp file
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                    print(f"Removed temporary file: {temp_file}")
        except Exception as e:
            print(f"Error downloading file: {str(e)}")
            import traceback
            print(traceback.format_exc())
            continue
    
    # Verify results
    print("\nVerifying processed files in OneDrive...")
    processed_files = await graph_client.list_files_in_folder(processed_folder)
    print(f"\nFound {len(processed_files)} files in {processed_folder}:")
    for file in processed_files:
        print(f"- {file['name']}")
    
    log(f"\nProcessed {len(processed_files)} of {len(files)} files.")
    log(f"Results are available in OneDrive folder: {processed_folder}")
    
    # List files in processed folder to verify
    log(f"\nVerifying files in processed folder: {processed_folder}")
    processed_files = await graph_client.list_files_in_folder(processed_folder)
    log(f"Files found in processed folder: {[f['name'] for f in processed_files]}")
    # No assertions: manual review only 