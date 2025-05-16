"""
Tests for the DocumentProcessor class.
"""

import asyncio
import os
import pytest
import json
from core.graph_1_1_0.main import GraphClient
from core.processing_1_2_0.processors.document_processor import DocumentProcessor
from core.utils.config import config
from httpx import HTTPStatusError

@pytest.fixture
def document_processor():
    """Create a DocumentProcessor instance for testing."""
    return DocumentProcessor(config["processing"])

@pytest.mark.asyncio
async def test_document_processing_workflow():
    """Test the complete document processing workflow for up to 10 documents:
    1. Read raw documents from OneDrive
    2. Process each document
    3. Verify each is saved to the processed folder as JSON
    4. Verify metadata and content
    """
    processor = DocumentProcessor(config["processing"])
    client = GraphClient()
    
    try:
        # Get source and target folders from config
        source_folder = config["onedrive"]["documents_folder"]
        target_folder = config["onedrive"]["processed_documents_folder"]
        user_email = os.getenv("USER_EMAIL")
        
        if not user_email:
            pytest.skip("USER_EMAIL environment variable not set")
        
        # Get access token
        access_token = await client._get_access_token()
        headers = {"Authorization": f"Bearer {access_token}"}
        
        try:
            # List files in source folder
            url = f"https://graph.microsoft.com/v1.0/users/{user_email}/drive/root:/{source_folder}:/children"
            response = await client.client.get(url, headers=headers)
            response.raise_for_status()
            items = response.json().get("value", [])
            
            # Filter for supported document types
            supported_extensions = ['.pdf', '.doc', '.docx', '.txt', '.rtf']
            doc_files = [
                item["name"] for item in items 
                if any(item["name"].lower().endswith(ext) for ext in supported_extensions)
            ]
            
            if not doc_files:
                pytest.skip("No supported document files found for testing")
            
            # Process up to 10 document files
            for file_name in doc_files[:10]:
                file_url = f"https://graph.microsoft.com/v1.0/users/{user_email}/drive/root:/{source_folder}/{file_name}:/content"
                response = await client.client.get(file_url, headers=headers, follow_redirects=True)
                response.raise_for_status()
                doc_bytes = response.content
                
                # Process the document with original filename
                result = await processor.process({
                    'content': doc_bytes,
                    'filename': file_name,
                    'content_type': processor._detect_content_type(file_name)
                })
                
                # Verify the result
                assert result['filename'].endswith('.json')
                assert result['filename'].startswith(os.path.splitext(file_name)[0])
                assert result['metadata'].text_content
                assert result['metadata'].one_drive_url  # Verify OneDrive URL was set
                
                # Verify the JSON file was uploaded to the correct folder
                verify_url = f"https://graph.microsoft.com/v1.0/users/{user_email}/drive/root:/{target_folder}/{result['filename']}"
                verify_response = await client.client.get(verify_url, headers=headers)
                verify_response.raise_for_status()
                
                # Verify the JSON content
                content_url = f"https://graph.microsoft.com/v1.0/users/{user_email}/drive/root:/{target_folder}/{result['filename']}:/content"
                content_response = await client.client.get(content_url, headers=headers, follow_redirects=True)
                content_response.raise_for_status()
                
                # Parse and verify JSON content
                json_content = json.loads(content_response.content)
                assert json_content['filename'] == result['filename']
                assert json_content['metadata']['text_content'] == result['metadata'].text_content
                assert json_content['metadata']['content_type'] == result['metadata'].content_type
                assert json_content['metadata']['size'] == result['metadata'].size
            
        except HTTPStatusError as e:
            if e.response.status_code == 404:
                pytest.skip("OneDrive folder not found. Please create the folder first.")
            raise
            
    except Exception as e:
        pytest.fail(f"Integration test failed: {str(e)}")

if __name__ == "__main__":
    pytest.main([__file__]) 