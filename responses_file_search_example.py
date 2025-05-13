import os
from openai import OpenAI

api_key          = os.getenv("OPENAI_API_KEY")
vector_store_id  = os.getenv("OPENAI_VECTOR_STORE_ID")
author           = "thomas.stolper@systemacro.com"

client = OpenAI(api_key=api_key)

resp = client.responses.create(
    model="gpt-4o",
    input=f"Show me all files by author {author}",
    tools=[{
        "type": "file_search",
        "vector_store_ids": [vector_store_id],
        "filters": {               # ← put filters here
            "author": author
        }
    }]
)


print(resp.output_text)          # answer text
print(resp.citations)            # matched chunks / files
