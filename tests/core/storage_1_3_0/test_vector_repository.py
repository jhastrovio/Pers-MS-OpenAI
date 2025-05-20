import os
os.environ["OPENAI_API_TYPE"] = "openai"

import pytest
from unittest.mock import patch
from core.storage_1_3_0.vector_repository import upload_to_openai_vector_store

def test_upload_to_openai_vector_store_success():
    sample_text = "Hello world"
    sample_metadata = {"filename": "test.txt", "author": "Test"}
    collection = "test-collection"
    fake_response = {"id": "doc-123", "status": "uploaded"}

    with patch("openai.vector_stores.documents.create", return_value=fake_response) as mock_create:
        response = upload_to_openai_vector_store(sample_text, sample_metadata, collection)
        mock_create.assert_called_once_with(
            vector_store_id=collection,
            file={
                "text": sample_text,
                "metadata": sample_metadata
            }
        )
        assert response == fake_response

def test_upload_to_openai_vector_store_failure():
    sample_text = "Hello world"
    sample_metadata = {"filename": "test.txt", "author": "Test"}
    collection = "test-collection"

    with patch("openai.vector_stores.documents.create", side_effect=Exception("API error")):
        with pytest.raises(RuntimeError) as excinfo:
            upload_to_openai_vector_store(sample_text, sample_metadata, collection)
        assert "Failed to upload to OpenAI vector store" in str(excinfo.value) 