"""Tests for the DocumentProcessor class."""

import pytest
import os
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from core.processing_1_2_0.processors.document_processor import DocumentProcessor
from core.processing_1_2_0.engine.base import ProcessingError, ValidationError
from core.graph_1_1_0.metadata import EmailDocumentMetadata

@pytest.fixture
def test_config():
    """Test configuration."""
    return {
        "FOLDERS": {
            "PROCESSED_DOCUMENTS": "data_PMSA/processed_documents_2",
            "DOCUMENTS": "data_PMSA/documents_1"
        },
        "CONTENT_TYPES": {
            "PDF": "application/pdf",
            "DOCX": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "TXT": "text/plain"
        },
        "TEXT_CLEANING": {
            "REMOVE_EXTRA_WHITESPACE": True,
            "NORMALIZE_LINE_ENDINGS": True,
            "REMOVE_CONTROL_CHARS": True
        },
        "user": {
            "email": "test@example.com"
        }
    }

@pytest.fixture
def mock_graph_client():
    """Mock GraphClient."""
    mock = Mock()
    mock.file_exists = AsyncMock(return_value=True)
    mock.upload_file = AsyncMock(return_value="https://example.com/test.json")
    return mock

@pytest.fixture
def document_processor(test_config, mock_graph_client):
    """Create a DocumentProcessor instance for testing."""
    with patch('core.processing_1_2_0.processors.document_processor.GraphClient', return_value=mock_graph_client):
        processor = DocumentProcessor(test_config)
        return processor

@pytest.mark.asyncio
async def test_process_document_with_file_path(document_processor, tmp_path):
    """Test processing a document from file path."""
    # Create a test file
    test_file = tmp_path / "test.txt"
    test_file.write_text("Test content")
    
    # Process the document
    result = await document_processor.process(str(test_file))
    
    # Verify the result
    assert isinstance(result, dict)
    assert "filename" in result
    assert "metadata" in result
    assert "content" in result
    assert "file_path" in result
    
    # Verify metadata
    metadata = result["metadata"]
    assert isinstance(metadata, EmailDocumentMetadata)
    assert metadata.type == "document"
    assert metadata.text_content == "Test content"
    assert metadata.one_drive_url == "https://example.com/test.json"

@pytest.mark.asyncio
async def test_process_document_with_raw_content(document_processor):
    """Test processing a document from raw content."""
    # Test data
    content = b"Test content"
    filename = "test.txt"
    
    # Process the document
    result = await document_processor.process({
        "content": content,
        "filename": filename
    })
    
    # Verify the result
    assert isinstance(result, dict)
    assert "filename" in result
    assert "metadata" in result
    assert "content" in result
    assert "file_path" in result
    
    # Verify metadata
    metadata = result["metadata"]
    assert isinstance(metadata, EmailDocumentMetadata)
    assert metadata.type == "document"
    assert metadata.text_content == "Test content"
    assert metadata.one_drive_url == "https://example.com/test.json"

@pytest.mark.asyncio
async def test_process_invalid_file(document_processor):
    """Test processing an invalid file."""
    with pytest.raises(ProcessingError):
        await document_processor.process("nonexistent.txt")

@pytest.mark.asyncio
async def test_process_invalid_content(document_processor):
    """Test processing invalid content."""
    with pytest.raises(ValidationError):
        await document_processor.process({
            "content": b"Test content"
            # Missing filename
        })

@pytest.mark.asyncio
async def test_clean_text_content(document_processor):
    """Test text content cleaning."""
    # Test data with extra whitespace and control characters
    text = "Test  content\r\nwith\tcontrol\x00chars"
    
    # Clean the text
    cleaned = document_processor._clean_text_content(text)
    
    # Verify the result
    assert cleaned == "Test content with controlchars"

@pytest.mark.asyncio
async def test_detect_content_type(document_processor):
    """Test content type detection."""
    # Test various file extensions
    assert document_processor._detect_content_type("test.pdf") == "application/pdf"
    assert document_processor._detect_content_type("test.docx") == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    assert document_processor._detect_content_type("test.txt") == "text/plain"
    assert document_processor._detect_content_type("test.xyz") == "application/octet-stream" 