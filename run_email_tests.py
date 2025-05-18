"""
Run multiple email processor tests.

This script processes multiple emails from the configured OneDrive folder and tests the 
email processor functionality.
"""

import asyncio
import os
import sys
from core.graph_1_1_0.main import GraphClient
from core.processing_1_2_0.processors.email_processor import EmailProcessor
from core.utils.config import config
from core.utils.onedrive_utils import list_folder_contents
from core.utils.ms_graph_client import GraphClient as MsGraphClient

async def process_emails(num_emails=10):
    """Process multiple emails from OneDrive and print results.
    
    Args:
        num_emails: Number of emails to process
    """
    processor = EmailProcessor(config)
    client = GraphClient()
    ms_client = MsGraphClient()
    
    try:
        # Get a real message from OneDrive
        user_email = config["user"]["email"]
        print(f"Running test for user: {user_email}")
        
        # List files in the emails folder to find .eml files
        emails_folder = config["onedrive"]["emails_folder"]
        print(f"Listing files in folder: {emails_folder}")
        files = await list_folder_contents(emails_folder)
        
        # Find .eml files
        eml_files = [f for f in files if f["name"].endswith(".eml")]
        if not eml_files:
            print(f"No .eml files found in OneDrive folder: {emails_folder}")
            return
            
        print(f"Found {len(eml_files)} .eml files")
        
        # Process up to num_emails
        files_to_process = eml_files[:num_emails]
        print(f"Processing {len(files_to_process)} emails")
        
        for i, eml_file in enumerate(files_to_process):
            print(f"\n--- Processing email {i+1}/{len(files_to_process)}: {eml_file['name']} ---")
            
            # Download the .eml file bytes
            eml_bytes = await ms_client.download_file_from_onedrive(emails_folder, eml_file["name"])
            
            # Process the email
            result = await processor.process(eml_bytes, user_email)
            
            # Verify the result
            print(f"Processed email: {result['subject']}")
            print(f"Saved to: {result['filename']}")
            print(f"OneDrive URL: {result['metadata'].get('one_drive_url', 'Not available')}")
            print(f"Outlook URL: {result['metadata'].get('outlook_url', 'Not available')}")
            
            # Verify the processed file exists in OneDrive
            processed_folder = config["onedrive"]["processed_emails_folder"]
            processed_path = f"{processed_folder}/{result['filename']}"
            file_exists = await client.file_exists(processed_path)
            print(f"File exists in OneDrive: {file_exists}")
            
            # Extract first 100 chars of text content
            text_preview = result['metadata'].get('text_content', '')[:100] + "..." if result['metadata'].get('text_content') else 'No text content'
            print(f"Text preview: {text_preview}")
            
    except Exception as e:
        print(f"Error processing emails: {str(e)}")
    finally:
        await processor.close()
        await ms_client.client.aclose()
        await client.close()

if __name__ == "__main__":
    # Get the number of emails to process from command line args or default to 10
    num_emails = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    asyncio.run(process_emails(num_emails)) 