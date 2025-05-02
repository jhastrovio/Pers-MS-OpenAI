# config/paths.py

from pathlib import Path

# Use local directory only
BASE_DIR = Path("C:/Users/JamesHassett/Dev/personal-ms-assistant")

# Raw data directories
RAW_EMAIL_DIR = BASE_DIR / "data" / "raw_1" / "emails"
RAW_DOCUMENT_DIR = BASE_DIR / "data" / "raw_1" / "documents"
RAW_STRUCTURED_DIR = BASE_DIR / "data" / "raw_1" / "structured"

# Ingested data files
INGESTED_EMAIL_FILE = BASE_DIR / "data" / "ingested_2" / "emails" / "email_chunks.jsonl"
INGESTED_DOCUMENT_FILE = BASE_DIR / "data" / "ingested_2" / "documents" / "document_chunks.jsonl"
INGESTED_STRUCTURED_FILE = BASE_DIR / "data" / "ingested_2" / "structured" / "structured_chunks.jsonl"

# Chunked data files
CHUNKED_EMAIL_FILE = BASE_DIR / "data" / "chunks_3" / "emails" / "email_chunks.jsonl"
CHUNKED_DOCUMENT_FILE = BASE_DIR / "data" / "chunks_3" / "documents" / "doc_chunks.jsonl"
CHUNKED_STRUCTURED_FILE = BASE_DIR / "data" / "chunks_3" / "structured" / "structured_chunks.jsonl"

# Index directories
INDEX_EMAIL_DIR = BASE_DIR / "data" / "index_5" / "email"
INDEX_DOCUMENT_DIR = BASE_DIR / "data" / "index_5" / "document"
INDEX_STRUCTURED_DIR = BASE_DIR / "data" / "index_5" / "structured"
INDEX_DIR = BASE_DIR / "data" / "index_5"  # for unified index (used in retriever.py)

# Metadata schema files
METADATA_SCHEMA_MD = BASE_DIR / "config" / "schema" / "metadata_schema.md"
METADATA_SCHEMA_JSON = BASE_DIR / "config" / "schema" / "metadata_schema.json"

# Embeddings directory
EMBEDDING_DIR = BASE_DIR / "data" / "embeddings_4"

# Logs
LOG_DIR = BASE_DIR / "logs"
