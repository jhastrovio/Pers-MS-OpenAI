# Microsoft Graph Integration (1.1.0)

## Overview
Handles integration with Microsoft Graph API for email and document retrieval. This component is responsible for:
- Email extraction and attachment handling
- OneDrive document synchronization
- MSAL authentication setup

## Dependencies
- Microsoft Authentication Library (MSAL)
- Microsoft Graph SDK
- Azure AD application registration

## Configuration
Required environment variables:
- `AZURE_CLIENT_ID`
- `AZURE_CLIENT_SECRET`
- `AZURE_TENANT_ID`

## Usage
```python
from core.graph_1_1_0.main import GraphClient

client = GraphClient()
emails = client.get_emails()
documents = client.get_documents()
```

## Roadmap Reference
See `ROADMAP.md` for detailed implementation status and future work.
