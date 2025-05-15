import os
from openai import OpenAI

def search_vectorstore(query, attributes_filter=None, limit=20):
    api_key = os.getenv("OPENAI_API_KEY")
    vector_store_id = os.getenv("OPENAI_VECTOR_STORE_ID")
    if not api_key or not vector_store_id:
        print("Please set OPENAI_API_KEY and OPENAI_VECTOR_STORE_ID in your .env or environment.")
        return
    client = OpenAI(api_key=api_key)
    results = client.vector_stores.search(
        vector_store_id=vector_store_id,
        query=query,
        filter=attributes_filter or {},
        limit=limit
    )
    print(f"Found {len(results.data)} results for query '{query}' and filter {attributes_filter}:")
    for r in results.data:
        print(r.attributes)
        print("-" * 40)

if __name__ == "__main__":
    # Example usage: search for author
    search_vectorstore(
        query="",  # Empty string for all
        attributes_filter={"author": "thomas.stolper@systemacro.com"},
        limit=20
    ) 