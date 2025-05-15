import os
from openai import OpenAI
from typing import Optional, Dict, Tuple


def upload_to_vectorstore(
    file_path: str,
    attributes: Dict,
    vector_store_id: Optional[str] = None,
    api_key: Optional[str] = None,
) -> Tuple[str, str]:
    """
    Upload a file to an OpenAI vector store with metadata (attributes).
    Creates a vector store if vector_store_id is not provided.
    Returns (file_id, vector_store_id).
    """
    # Use API key from argument or environment
    api_key = api_key or os.getenv("OPENAI_API_KEY")
    assert api_key, "OPENAI_API_KEY not found in .env or argument"
    client = OpenAI(api_key=api_key)

    # Create vector store if needed
    if not vector_store_id:
        vs = client.vector_stores.create(name="Auto Vector Store")
        vector_store_id = vs.id

    # Upload file
    with open(file_path, "rb") as f:
        file_obj = client.files.create(file=f, purpose="assistants")

    # Attach file to vector store with attributes
    vs_file = client.vector_stores.files.create(
        vector_store_id=vector_store_id,
        file_id=file_obj.id,
        attributes=attributes
    )

    return file_obj.id, vector_store_id

# Example usage (remove or comment out in production)
if __name__ == "__main__":
    file_id, vs_id = upload_to_vectorstore(
        file_path="data/Deep_Dive.pdf",
        attributes={
            "title": "Deep Dive – Trump's Policy Inconsistencies and Risks for the Dollar",
            "source": "SYSTEMACRO Research",
            "filetype": "pdf"
        }
    )
    print(f"Uploaded file {file_id} to vector store {vs_id}") 