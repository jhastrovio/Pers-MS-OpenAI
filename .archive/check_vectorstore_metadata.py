import os
from openai import OpenAI
import csv

# Load API key and vector store ID from environment variables
api_key = os.getenv("OPENAI_API_KEY")
vector_store_id = os.getenv("OPENAI_VECTOR_STORE_ID")

if not api_key or not vector_store_id:
    print("Please set OPENAI_API_KEY and OPENAI_VECTOR_STORE_ID in your .env or environment.")
    exit(1)

client = OpenAI(api_key=api_key)

# List files in the vector store and collect their metadata
data = []
all_keys = set()
files = client.vector_stores.files.list(vector_store_id=vector_store_id)
for f in files.data:
    meta = f.attributes or {}
    meta["file_id"] = f.id  # Add file_id for traceability
    data.append(meta)
    all_keys.update(meta.keys())

# Standardize columns (sorted for readability)
columns = sorted(all_keys)

# Write to CSV
csv_path = "vectorstore_metadata.csv"
with open(csv_path, "w", newline='', encoding="utf-8") as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=columns)
    writer.writeheader()
    for row in data:
        # Fill missing keys with empty string
        writer.writerow({k: row.get(k, "") for k in columns})

print(f"Metadata exported to {csv_path}") 