import os
import openai
from typing import Dict, Any

openai.api_key = os.getenv("OPENAI_API_KEY")


def upload_to_openai_vector_store(text: str, metadata: Dict[str, Any], collection: str) -> Any:
    """
    Uploads a document (text + metadata) to the OpenAI vector store.
    Args:
        text: The text content to embed and store.
        metadata: Dictionary of metadata to store alongside the embedding.
        collection: The OpenAI vector store (collection) ID or name.
    Returns:
        The OpenAI API response object.
    Raises:
        openai.OpenAIError: If the API call fails.
    """
    try:
        response = openai.vector_stores.documents.create(
            vector_store_id=collection,
            file={
                "text": text,
                "metadata": metadata
            }
        )
        return response
    except Exception as e:
        # Log or handle as appropriate for your project
        raise RuntimeError(f"Failed to upload to OpenAI vector store: {e}") 