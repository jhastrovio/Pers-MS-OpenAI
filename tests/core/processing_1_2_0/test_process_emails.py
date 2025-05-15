import asyncio
import os
from core.graph_1_1_0.main import GraphClient
from core.processing_1_2_0.process_emails import (
    list_raw_eml_files,
    download_eml_file,
    process_eml_content,
    upload_processed_eml,
    upload_attachment,
    process_all_emails
)

async def test_email_processing():
    """Test the email processing pipeline."""
    print("\nStarting email processing test...")
    
    # Initialize the Graph client
    client = GraphClient()
    
    try:
        # 1. List files in the raw emails folder
        print("\nListing raw .eml files...")
        eml_files = await list_raw_eml_files(client)
        print(f"Found {len(eml_files)} .eml files")
        for file in eml_files:
            print(f"- {file}")
            
        if not eml_files:
            print("No .eml files found to process")
            return
            
        # Process all files
        for i, test_file in enumerate(eml_files, 1):
            print(f"\nProcessing file {i}/{len(eml_files)}: {test_file}")
            
            try:
                # Download the file
                print("Downloading file...")
                eml_bytes = await download_eml_file(client, test_file)
                print(f"Downloaded {len(eml_bytes)} bytes")
                
                # Process the content
                print("Processing email content...")
                processed = await process_eml_content(eml_bytes)
                print(f"Processed email: {processed['filename']}")
                print(f"Subject: {processed['metadata'].subject}")
                print(f"From: {processed['metadata'].from_}")
                print(f"Date: {processed['metadata'].date}")
                print(f"Attachments: {len(processed['attachments'])}")
                print(f"Text content length: {len(processed['metadata'].text_content)}")
                
                # Upload the processed email metadata
                print("Uploading processed email metadata...")
                result = await upload_processed_eml(
                    client,
                    processed['filename'],
                    processed['eml_bytes'],
                    processed['metadata']
                )
                print(f"Uploaded metadata to: {result['one_drive_url']}")
                
                # Upload any attachments
                if processed['attachments']:
                    print("Uploading attachments...")
                    for attachment in processed['attachments']:
                        print(f"Uploading {attachment['filename']}...")
                        att_result = await upload_attachment(
                            client,
                            attachment['filename'],
                            attachment['bytes'],
                            attachment['metadata']
                        )
                        print(f"Uploaded to: {att_result['one_drive_url']}")
                
                print(f"Successfully processed file {i}/{len(eml_files)}")
                
            except Exception as e:
                print(f"Error processing {test_file}: {str(e)}")
                continue
        
        print("\nAll files processed!")
        
    except Exception as e:
        print(f"\nError during test: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(test_email_processing()) 