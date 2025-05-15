# FastAPI Backend (1.4.0)

## Overview
Provides the API layer for the application. This component is responsible for:
- Health check endpoints
- RAG endpoint implementation
- Error handling and logging
- API documentation

## Dependencies
- FastAPI
- Uvicorn
- Pydantic for request/response models
- Application Insights for monitoring

## Configuration
- API settings in `config/api/`
- Environment variables for deployment
- CORS and security settings

## Usage
```python
from core.api_1_4_0.main import app

# Run with uvicorn
# uvicorn core.1_4_0_api.main:app --reload
```

## API Endpoints
- `GET /health` - Health check
- `POST /rag` - RAG query endpoint
- `GET /docs` - API documentation (Swagger UI)

## Roadmap Reference
See `ROADMAP.md` for detailed implementation status and future work.
