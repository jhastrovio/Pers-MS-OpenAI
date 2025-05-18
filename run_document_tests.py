"""
Run document processor tests.

This script processes documents from the configured OneDrive folder and tests the
document processor functionality.
"""

import asyncio
import os
import sys
from core.graph_1_1_0.main import GraphClient
from core.processing_1_2_0.processors.document_processor import DocumentProcessor
from core.utils.config import config
from core.utils.ms_graph_client import GraphClient as MsGraphClient

async def process_documents(num_documents=3):
    """Process multiple documents from OneDrive and print results.
    
    Args:
        num_documents: Number of documents to process
    """
    # Make sure config has the required fields from BaseProcessor
    test_config = config.copy()
    # Move processing config fields to the top level for BaseProcessor
    if 'processing' in test_config and 'MAX_FILE_SIZE' not in test_config:
        test_config['MAX_FILE_SIZE'] = test_config['processing']['MAX_FILE_SIZE']
        test_config['ALLOWED_EXTENSIONS'] = test_config['processing']['ALLOWED_EXTENSIONS']
    
    processor = DocumentProcessor(test_config)
    client = GraphClient()
    ms_client = MsGraphClient()
    
    try:
        # List documents in the source folder
        user_email = config["user"]["email"]
        folder_path = config["onedrive"]["documents_folder"]
        
        # Get list of files from OneDrive
        folder_items = await ms_client.list_files_in_folder(folder_path)
        
        if not folder_items:
            print(f"No files found in folder: {folder_path}")
            return
        
        # Filter for document files
        document_extensions = ['.pdf', '.doc', '.docx', '.txt', '.rtf', '.xlsx', '.xls', '.csv']
        document_files = [
            item for item in folder_items 
            if any(item['name'].lower().endswith(ext) for ext in document_extensions)
        ]
        
        if not document_files:
            print(f"No document files found in folder: {folder_path}")
            return
        
        # Process at most num_documents documents
        count = 0
        for doc in document_files[:num_documents]:
            try:
                # Download document content
                doc_name = doc['name']
                print(f"\nProcessing document: {doc_name}")
                
                # Download the file to a temporary location
                download_path = f"temp_{doc_name}"
                download_url = f"https://graph.microsoft.com/v1.0/users/{user_email}/drive/root:/{folder_path}/{doc_name}:/content"
                
                access_token = await client._get_access_token()
                headers = {"Authorization": f"Bearer {access_token}"}
                
                response = await client.client.get(download_url, headers=headers, follow_redirects=True)
                response.raise_for_status()
                
                # Save to temp file
                with open(download_path, 'wb') as f:
                    f.write(response.content)
                
                # Process the document
                result = await processor.process(download_path)
                
                # Clean up temp file
                if os.path.exists(download_path):
                    os.remove(download_path)
                
                # Print the result
                print(f"Document processed successfully: {doc_name}")
                print(f"Result filename: {result['filename']}")
                print(f"Metadata:")
                for key, value in result['metadata'].items():
                    if key == 'text_content':
                        # Truncate text content for display
                        text = value[:200] + "..." if value and len(value) > 200 else value
                        print(f"  {key}: {text}")
                    else:
                        print(f"  {key}: {value}")
                
                # Increment the counter
                count += 1
                
            except Exception as e:
                print(f"Error processing document {doc['name']}: {str(e)}")
        
        print(f"\nProcessed {count} documents.")
            
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        await client.close()

if __name__ == "__main__":
    num_documents = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    asyncio.run(process_documents(num_documents)) 