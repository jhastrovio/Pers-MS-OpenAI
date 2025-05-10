# Personal MS ChatGPT – RAG Patterns Reference

Version: 10 May 2025

---

## 🎯 Purpose

This document summarizes useful RAG (Retrieval-Augmented Generation) code patterns adapted from OpenAI demos and best practices for use in the Personal MS ChatGPT project.

---

## 📝 RAG with simple CSV retrieval

```python
import pandas as pd
from openai import OpenAI

client = OpenAI()
df = pd.read_csv("data.csv")

query = "What are the revenue numbers for Q1?"
matches = df[df["content"].str.contains("Q1")]

response = client.responses.create(
    model="gpt-4o",
    input=f"Relevant data: {matches}\nUser question: {query}"
)
print(response.output_text)
```

---

## 🔄 Multi-turn RAG chat with memory

```python
messages = [
    {"role": "system", "content": "You are a helpful assistant."}
]

while True:
    user_input = input("You: ")
    messages.append({"role": "user", "content": user_input})
    
    response = client.responses.create(
        model="gpt-4o",
        input=user_input
    )
    print("Assistant:", response.output_text)
```

---

## 📝 Document ingestion pipeline example

```python
from llama_index import Document
from openai import OpenAI

client = OpenAI()
docs = [Document(text="sample content to embed")]

# Simulated embedding step
embeddings = [client.embeddings.create(
    model="text-embedding-3-small",
    input=doc.text
).data[0].embedding for doc in docs]
```

---

## 💡 Hybrid retrieval (keyword + vector fusion)

```python
bm25_results = ["Doc A", "Doc B"]
vector_results = ["Doc B", "Doc C"]

# Reciprocal Rank Fusion (RRF) example
merged = list(dict.fromkeys(bm25_results + vector_results))
print("RRF merged results:", merged)
```

---

## ✅ Best Practices

* Always pre-clean documents (remove signatures, noise).
* Chunk long documents (\~500-800 tokens per chunk).
* Use embeddings only on clean, meaningful text.
* Apply reciprocal rank fusion when combining retrieval methods.

---

Last updated: 10 May 2025
