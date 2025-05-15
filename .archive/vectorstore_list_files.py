import os
from openai import OpenAI
from dotenv import load_dotenv

# Load API key and vector store ID from .env
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
vector_store_id = os.getenv("OPENAI_VECTOR_STORE_ID")
assert api_key, "OPENAI_API_KEY not found in .env"
assert vector_store_id, "OPENAI_VECTOR_STORE_ID not found in .env"

client = OpenAI(api_key=api_key)

print(f"Listing files in vector store: {vector_store_id}\n")

files = client.vector_stores.files.list(vector_store_id=vector_store_id)

print(f"Found {len(files.data)} files:")
print(f"{'File ID':<30}  {'Attributes/Metadata'}")
print("-" * 80)
for f in files.data:
    print(f"{f.id:<30}  {f.attributes}") 