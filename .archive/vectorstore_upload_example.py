import os
import time
from openai import OpenAI
from dotenv import load_dotenv

# Load API key from .env
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
assert api_key, "OPENAI_API_KEY not found in .env"

# Initialize the OpenAI client
client = OpenAI(api_key=api_key)

# Path to your local file
file_path = r"data/Deep_Dive.pdf"

# Metadata to attach to the file (as attributes)
file_attributes = {
    "title": "Deep Dive – Trump's Policy Inconsistencies and Risks for the Dollar",
    "source": "SYSTEMACRO Research",
    "filetype": "pdf"
}

if __name__ == "__main__":
    # Step 1: Create a vector store
    print("Creating vector store...")
    vector_store = client.vector_stores.create(name="Test Vector Store (SDK)")
    print(f"Vector store created: {vector_store.id}")

    # Step 2: Upload file
    print("Uploading file...")
    with open(file_path, "rb") as f:
        file_obj = client.files.create(
            file=f,
            purpose="assistants"
        )
    print(f"File uploaded: {file_obj.id}")

    # Step 3: Add file to vector store with attributes (metadata)
    print("Adding file to vector store with attributes...")
    vs_file = client.vector_stores.files.create(
        vector_store_id=vector_store.id,
        file_id=file_obj.id,
        attributes=file_attributes
    )
    print(f"File added to vector store: {vs_file.id}")

    # Wait for the file to be processed
    print("\nWaiting for file to be processed (10 seconds)...")
    time.sleep(10)

    # Step 4: Basic search without filters
    print("\nSearching without filters...")
    try:
        results = client.vector_stores.search(
            vector_store_id=vector_store.id,
            query="policy inconsistencies"
        )
        print(f"Found {len(results.data)} results:")
        for i, result in enumerate(results.data):
            print(f"{i+1}. Score: {result.score:.4f}, File: {result.file_id}")
    except Exception as e:
        print(f"Search error: {e}")

    # Note about filtering
    print("\nNote: For filtering by metadata attributes, please check the latest OpenAI API documentation.")
    print("The filter parameter format may have changed since this script was created.")
    print("See: https://platform.openai.com/docs/api-reference/vector-stores")

    print("\nDone!") 