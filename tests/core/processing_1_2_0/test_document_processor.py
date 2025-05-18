"""
Tests for the DocumentProcessor class.
"""

import asyncio
import os
import pytest
import json
from unittest.mock import patch, MagicMock
from core.graph_1_1_0.main import GraphClient
from core.processing_1_2_0.processors.document_processor import DocumentProcessor
from core.utils.config import config
from httpx import HTTPStatusError
import uuid

@pytest.fixture
def document_processor():
    """Create a DocumentProcessor instance for testing."""
    # Ensure we have the required configuration keys
    test_config = config.copy()
    
    # Make sure processing config has the required fields
    if 'MAX_FILE_SIZE' not in test_config:
        test_config['MAX_FILE_SIZE'] = 50 * 1024 * 1024  # 50MB
    
    if 'ALLOWED_EXTENSIONS' not in test_config:
        test_config['ALLOWED_EXTENSIONS'] = {
            '.pdf', '.docx', '.doc', '.pptx', '.ppt', 
            '.xlsx', '.xls', '.csv', '.txt', '.html'
        }
    
    return DocumentProcessor(test_config)

@pytest.fixture
def mock_graph_client():
    """Create a mock GraphClient for testing."""
    mock_client = MagicMock()
    
    # Mock the upload_file method
    mock_client.upload_file.return_value = asyncio.Future()
    mock_client.upload_file.return_value.set_result("https://tassehcapital-my.sharepoint.com/example/url")
    
    # Mock the file_exists method
    mock_client.file_exists.return_value = asyncio.Future()
    mock_client.file_exists.return_value.set_result(False)
    
    # Mock the _get_access_token method
    mock_client._get_access_token.return_value = asyncio.Future()
    mock_client._get_access_token.return_value.set_result("mock_access_token")
    
    # Mock client.put response
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {"webUrl": "https://tassehcapital-my.sharepoint.com/example/url"}
    
    mock_client.client = MagicMock()
    mock_client.client.put.return_value = asyncio.Future()
    mock_client.client.put.return_value.set_result(mock_response)
    
    return mock_client

@pytest.mark.asyncio
async def test_document_processing_unit(document_processor, mock_graph_client, tmp_path):
    """Test the document processor with mocked dependencies."""
    # Create a test document
    test_file = tmp_path / "test_document.txt"
    test_file.write_text("This is a test document.")
    
    # Add additional mocks for the TextExtractor and MetadataExtractor
    with patch("core.processing_1_2_0.processors.document_processor.TextExtractor") as mock_text_extractor, \
         patch("core.processing_1_2_0.processors.document_processor.MetadataExtractor") as mock_metadata_extractor, \
         patch.object(document_processor, 'graph_client', mock_graph_client), \
         patch('uuid.uuid4', return_value='test-uuid'):
        
        # Configure mocks
        mock_text_extractor.extract_text.return_value = "This is a test document."
        mock_metadata_extractor.extract_metadata.return_value = {
            "title": "Test Document",
            "author": "Test Author",
            "last_modified": "2023-01-01T00:00:00Z"
        }
        
        # Process the document
        result = await document_processor.process(str(test_file))
        
        # Verify the result
        assert result['filename'].endswith('.json')
        assert 'metadata' in result
        assert result['content'] == str(test_file)
        
        # Verify the metadata
        metadata = result['metadata']
        assert metadata['document_id'] == 'test-uuid'
        assert metadata['type'] == 'document'
        assert metadata['text_content'] == "This is a test document."
        assert metadata['one_drive_url']
        assert metadata['title'] == "Test Document"
        assert metadata['author'] == "Test Author"

@pytest.mark.asyncio
async def test_document_processing_workflow():
    """Test the full document processing workflow with real dependencies."""
    # Skip this test if we're not in a real environment
    if not os.path.exists("test_document.pdf"):
        pytest.skip("No test document available")
    
    processor = DocumentProcessor(config)
    client = GraphClient()
    
    try:
        # Get a test file path
        file_path = "test_document.pdf"  # Replace with a real file path
        user_email = config["user"]["email"]
        
        # Process the document
        result = await processor.process(file_path, user_email)
        
        # Verify the result
        assert result['filename'].endswith('.json')
        assert result['content'] == file_path
        assert result['metadata']['text_content']
        assert result['metadata']['one_drive_url']  # Verify OneDrive URL was set
        
        # Verify the JSON file was uploaded to the correct folder
        verify_url = f"https://graph.microsoft.com/v1.0/users/{user_email}/drive/root:/{config['onedrive']['processed_documents_folder']}/{result['filename']}"
        verify_response = await client.client.get(verify_url, headers={"Authorization": f"Bearer {await client._get_access_token()}"})
        verify_response.raise_for_status()
        
        # Verify the JSON content
        content_url = f"https://graph.microsoft.com/v1.0/users/{user_email}/drive/root:/{config['onedrive']['processed_documents_folder']}/{result['filename']}:/content"
        content_response = await client.client.get(content_url, headers={"Authorization": f"Bearer {await client._get_access_token()}"}, follow_redirects=True)
        content_response.raise_for_status()
        
        # Parse and verify JSON content
        json_content = json.loads(content_response.content)
        assert 'metadata' in json_content
        assert json_content['metadata']['document_id']
        assert json_content['metadata']['text_content']
        assert json_content['metadata']['type'] == 'document'
        assert json_content['metadata']['one_drive_url']
        
    except Exception as e:
        pytest.fail(f"Integration test failed: {str(e)}")

@pytest.mark.asyncio
async def test_clean_text_content(document_processor):
    """Test the _clean_text_content method."""
    # Text with headers, footers, and boilerplate content
    text = """Page 1
Confidential
This is the actual content.
This is repeated content.
This is repeated content.
This site uses cookies
Copyright 2023
www.example.com
This is just a number: 123
Privacy Policy: We may request cookies
"""
    
    cleaned_text = document_processor._clean_text_content(text)
    
    # Verify headers, footers, and boilerplate were removed
    assert "Page 1" not in cleaned_text
    assert "Confidential" not in cleaned_text
    assert "This is repeated content." not in cleaned_text
    assert "This site uses cookies" not in cleaned_text
    assert "Copyright 2023" not in cleaned_text
    assert "Privacy Policy" not in cleaned_text
    
    # Verify actual content was kept
    assert "This is the actual content." in cleaned_text
    
    # Test with URL content
    url_text = "This is important content with multiple words and a URL: https://example.com/page."
    cleaned_url_text = document_processor._clean_text_content(url_text)
    assert url_text in cleaned_url_text

@pytest.mark.asyncio
async def test_upload_to_onedrive(document_processor, mock_graph_client):
    """Test the _upload_to_onedrive method."""
    with patch.object(document_processor, 'graph_client', mock_graph_client):
        result = await document_processor._upload_to_onedrive("test.txt", b"Test content", "test_folder")
        
        # Verify the GraphClient was called correctly
        mock_graph_client._get_access_token.assert_called_once()
        mock_graph_client.client.put.assert_called_once()
        
        # Verify the result
        assert result == "https://tassehcapital-my.sharepoint.com/example/url"

if __name__ == "__main__":
    pytest.main([__file__]) 