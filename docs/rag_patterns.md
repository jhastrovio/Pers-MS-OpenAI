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
import logging
from typing import List, Dict

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
CSV_CONFIG = {
    "encoding": "utf-8",
    "chunk_size": 1000,
    "max_retries": 3,
    "retry_delay": 1
}

def retrieve_from_csv(query: str, csv_path: str) -> List[Dict]:
    try:
        df = pd.read_csv(csv_path, encoding=CSV_CONFIG["encoding"])
        matches = df[df["content"].str.contains(query, case=False, na=False)]
        return matches.to_dict("records")
    except Exception as e:
        logger.error(f"Error reading CSV: {e}")
        raise

def get_rag_response(query: str, matches: List[Dict]) -> str:
    client = OpenAI()
    try:
        response = client.responses.create(
            model="gpt-4o",
            input=f"Relevant data: {matches}\nUser question: {query}"
        )
        return response.output_text
    except Exception as e:
        logger.error(f"Error getting RAG response: {e}")
        raise

# Usage
query = "What are the revenue numbers for Q1?"
matches = retrieve_from_csv(query, "data.csv")
response = get_rag_response(query, matches)
print(response)
```

---

## 🔄 Multi-turn RAG chat with memory

```python
from openai import OpenAI
import logging
from typing import List, Dict
import json

# Configuration
CHAT_CONFIG = {
    "model": "gpt-4o",
    "max_tokens": 1000,
    "temperature": 0.7,
    "max_history": 10
}

class RAGChat:
    def __init__(self):
        self.client = OpenAI()
        self.messages = [
            {"role": "system", "content": "You are a helpful assistant."}
        ]
        self.history = []

    def add_to_history(self, message: Dict):
        self.history.append(message)
        if len(self.history) > CHAT_CONFIG["max_history"]:
            self.history.pop(0)

    def get_response(self, user_input: str) -> str:
        try:
            self.messages.append({"role": "user", "content": user_input})
            
            response = self.client.responses.create(
                model=CHAT_CONFIG["model"],
                input=user_input,
                max_tokens=CHAT_CONFIG["max_tokens"],
                temperature=CHAT_CONFIG["temperature"]
            )
            
            self.add_to_history({"role": "assistant", "content": response.output_text})
            return response.output_text
        except Exception as e:
            logger.error(f"Error in chat: {e}")
            raise

# Usage
chat = RAGChat()
while True:
    user_input = input("You: ")
    if user_input.lower() == "quit":
        break
    response = chat.get_response(user_input)
    print("Assistant:", response)
```

---

## 📝 Document ingestion pipeline example

```python
from llama_index import Document
from openai import OpenAI
import logging
from typing import List, Dict
import asyncio

# Configuration
INGESTION_CONFIG = {
    "chunk_size": 500,
    "chunk_overlap": 50,
    "embedding_model": "text-embedding-3-small",
    "batch_size": 10
}

class DocumentIngestion:
    def __init__(self):
        self.client = OpenAI()
        self.logger = logging.getLogger(__name__)

    async def process_document(self, doc: Document) -> Dict:
        try:
            embedding = await self.client.embeddings.create(
                model=INGESTION_CONFIG["embedding_model"],
                input=doc.text
            )
            return {
                "text": doc.text,
                "embedding": embedding.data[0].embedding,
                "metadata": doc.metadata
            }
        except Exception as e:
            self.logger.error(f"Error processing document: {e}")
            raise

    async def process_batch(self, docs: List[Document]) -> List[Dict]:
        tasks = [self.process_document(doc) for doc in docs]
        return await asyncio.gather(*tasks)

# Usage
docs = [Document(text="sample content to embed")]
ingestion = DocumentIngestion()
processed_docs = asyncio.run(ingestion.process_batch(docs))
```

---

## 💡 Hybrid retrieval (keyword + vector fusion)

```python
from typing import List, Dict
import numpy as np
from rank_bm25 import BM25Okapi
import logging

# Configuration
HYBRID_CONFIG = {
    "bm25_weight": 0.4,
    "vector_weight": 0.6,
    "top_k": 5,
    "min_score": 0.1
}

class HybridRetriever:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def bm25_search(self, query: str, documents: List[str]) -> List[float]:
        try:
            tokenized_docs = [doc.split() for doc in documents]
            bm25 = BM25Okapi(tokenized_docs)
            scores = bm25.get_scores(query.split())
            return scores
        except Exception as e:
            self.logger.error(f"BM25 search error: {e}")
            raise

    def vector_search(self, query_embedding: List[float], doc_embeddings: List[List[float]]) -> List[float]:
        try:
            scores = [np.dot(query_embedding, doc_emb) for doc_emb in doc_embeddings]
            return scores
        except Exception as e:
            self.logger.error(f"Vector search error: {e}")
            raise

    def combine_scores(self, bm25_scores: List[float], vector_scores: List[float]) -> List[float]:
        try:
            combined = [
                HYBRID_CONFIG["bm25_weight"] * bm25 + 
                HYBRID_CONFIG["vector_weight"] * vec
                for bm25, vec in zip(bm25_scores, vector_scores)
            ]
            return combined
        except Exception as e:
            self.logger.error(f"Score combination error: {e}")
            raise

# Usage
documents = ["Doc A", "Doc B", "Doc C"]
query = "example query"
retriever = HybridRetriever()

bm25_scores = retriever.bm25_search(query, documents)
vector_scores = retriever.vector_search(query_embedding, doc_embeddings)
final_scores = retriever.combine_scores(bm25_scores, vector_scores)

# Get top results
top_indices = np.argsort(final_scores)[-HYBRID_CONFIG["top_k"]:]
results = [documents[i] for i in top_indices if final_scores[i] > HYBRID_CONFIG["min_score"]]
```

---

## ✅ Best Practices

* Always pre-clean documents (remove signatures, noise).
* Chunk long documents (~500-800 tokens per chunk).
* Use embeddings only on clean, meaningful text.
* Apply reciprocal rank fusion when combining retrieval methods.

---

Last updated: 10 May 2025
