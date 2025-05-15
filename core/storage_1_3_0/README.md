# Storage Layer (1.3.0)

## Overview
Manages data storage and retrieval operations. This component is responsible for:
- OneDrive folder structure management
- JSON schema implementation
- JSONL batch processing
- Data persistence and retrieval

## Dependencies
- Microsoft Graph SDK for OneDrive operations
- JSON schema validation library
- File system operations

## Configuration
- Storage paths and schemas in `config/storage/`
- OneDrive folder structure configuration
- JSON schema definitions

## Usage
```python
from core.storage_1_3_0.main import StorageManager

storage = StorageManager()
storage.save_email(cleaned_email)
storage.save_document(processed_doc)
batch = storage.create_batch()
```

## Roadmap Reference
See `ROADMAP.md` for detailed implementation status and future work.
