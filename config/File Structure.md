# Project sturcture for subfolders C:\Users\JamesHassett\Dev\personal-ms-assistant\src and C:\Users\JamesHassett\Dev\personal-ms-assistant\config
C:\Users\JamesHassett\Dev\personal-ms-assistant\config
│   config.yaml
│   paths.py
│   secrets.json
│   secrets.py
│
├───schema
│       metadata_schema.json
│       metadata_schema.md
│

C:\Users\JamesHassett\Dev\personal-ms-assistant\src
│
├───embeddings
│   │   embed_azure.py
│   │   embed_chunks.py
│   │   embed_email_chunks.py
│   │   embed_structured_chunks.py
│   │   generate_answer.py
│   │   _init_.py
│   │
├───graph
│   │   auth.py
│   │   fetch_emails.py
│   │   fetch_onedrive.py
│   │   _init_.py   │
│
├───indexing
│   │   build_email_faiss.py
│   │   build_faiss_index.py
│   │   build_structured_faiss_index.py
│   │   faiss_utils.py
│   │   index_embeddings.py
│   │   __init__.py
│
├───ingestion
│   │   ingest_documents.py
│   │   ingest_emails.py
│   │   ingest_onedrive.py
│   │   ingest_structured.py
│   │   _init_.py   │
│
├───preprocessing
│   │   chunk_documents.py
│   │   chunk_emails.py
│   │   chunk_structured.py
│   │   _init_.py
│
├───rag
│   │   document_retriever.py
│   │   rag_api.py
│   │   structured_retriever.py
│   │   __init__.py
│   │
│
├───utils
│   │   chunking.py
│   │   extract_text.py
│   │   text_cleaning.py