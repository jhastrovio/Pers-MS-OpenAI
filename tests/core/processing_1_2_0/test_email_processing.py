import asyncio
import os
from core.utils.ms_graph_client import GraphClient
from core.utils.config import config
from core.processing_1_2_0.process_emails import (
    list_raw_eml_files,
    download_eml_file,
    process_eml_content,
    upload_processed_eml
)


async def test_email_processing():
    # Initialize the MSGraphClient
    client = GraphClient()
    
    # List available .eml files
    eml_files = await list_raw_eml_files(client)
    
    if not eml_files:
        print("No .eml files found in the emails folder.")
        return
    
    # Select the first .eml file
    first_eml = eml_files[0]
    print(f"Processing file: {first_eml}")
    
    # Download and process the file
    eml_bytes = await download_eml_file(client, first_eml)
    processed = await process_eml_content(eml_bytes)
    
    # Print metadata for verification
    print("\nEmail Metadata:")
    print(f"Subject: {processed['metadata'].subject}")
    print(f"From: {processed['metadata'].from_}")
    print(f"Date: {processed['metadata'].date}")
    
    if processed['metadata'].attachments:
        print("\nAttachments:")
        for att_id in processed['metadata'].attachments:
            print(f"- {att_id}")
    
    # Upload the processed email
    result = await upload_processed_eml(
        client,
        processed['filename'],
        processed['eml_bytes'],
        processed['metadata']
    )
    
    print(f"\nSaved processed email to {config['onedrive']['processed_emails_folder']}/{processed['filename']}")
    print(f"OneDrive URL: {result['one_drive_url']}")
    print(f"Created at: {result['created_at']}")


if __name__ == "__main__":
    asyncio.run(test_email_processing()) 