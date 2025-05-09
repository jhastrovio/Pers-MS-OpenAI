# Personal MS Assistant – Unified Roadmap (Rev. 09 May 2025)

## Goal
Operate a single ChatGPT assistant that searches & summarises Outlook e‑mails and OneDrive documents. The design must scale to larger data volumes and future task‑specific offshoots without re‑architecting.

---

### 0. Foundation (Complete, except Key Vault)
- [x] Repository, GitHub Actions CI, pre‑commit hooks
- [x] FastAPI skeleton (/health, /query) with MSAL OAuth (service‑principal) middleware
- [ ] Secrets in Azure Key Vault (**deferred**)
- [x] Application Insights attached to both dev & prod App Services

---

### 1. Core Orchestrator
- [ ] Intent classifier (email | drive | mixed)
- [ ] Response formatter with inline citations and confidence score
- [ ] Unit + integration tests (Mock‑Graph, httpx TestClient)

---

### 2. Retrieval via Responses API + File Search
- [ ] Create a single vector‑store (corp-kb, unlimited expiry)
- [ ] Converter scripts
- [ ] Outlook Graph delta → monthly .jsonl bundles (strip signatures)
- [ ] OneDrive watcher → direct pass‑through of PDFs/Docs
- [ ] ingest.py upload script – idempotent; polls status until completed

---

### 3. Live Sync & Budget Control
- [ ] Azure Function (5‑min cron) runs Graph delta sync, re‑uploads changed bundles
- [ ] "Top‑k + refine" retrieval wrapper (1 k tokens, fallback fetch on low confidence)
- [ ] Alerts: vector_store.file_count ≥ 9 500, spikes in usage.vector_store_bytes

---

### 4. ChatGPT Action & UX
- [ ] Publish Company‑Assistant action with file_search tool attached to the vector‑store
- [ ] Front‑end badges show filename • page for each citation
- [ ] Latency and precision dashboards in Application Insights

---

### 5. Security & Compliance Hardening
- [ ] OWASP ASVS threat‑model review
- [ ] Key‑vault rotation pipeline (90‑day schedule)
- [ ] Purview scan to redact PII before upload
- [ ] Audit log export to Log Analytics; cost and file‑count monitoring

---

### 6. Scale & Migration Path
- [ ] Trigger: file_count > 10 000 or > 300 queries/day average
- [ ] Evaluate Azure AI Search (hybrid BM25 + vector, ACL trimming)
- [ ] Re‑index into new store; swap vector_store_ids in the action with zero downtime

---

## Acceptance Criteria
| KPI                        | Target      |
|----------------------------|-------------|
| End‑to‑end latency         | ≤ 4 s       |
| Answer precision (manual)  | ≥ 80 %      |
| Cost per 100 queries       | < US$ 5     |
| Vector‑store file cap      | ≤ 10 000    |
| Security incidents         | 0           |

---

**Note:** Key Vault integration is deferred for now and can be added in a future phase.

## Project Overview
This project aims to create a ChatGPT Actions integration for the Personal MS Assistant, enabling seamless interaction between ChatGPT and the assistant's capabilities. The integration will allow ChatGPT to access and manipulate data through a well-defined API interface.

## End-to-End MVP Outline & Checklist

### 1. FastAPI Server
- [x] FastAPI app is created and running
- [x] CORS is configured (allowing ChatGPT to access the API)
- [x] Root endpoint ("/") returns a simple status message

### 2. Authentication (Basic)
- [x] API key in header implemented
- [x] Protect at least one endpoint with authentication

### 3. Data Action Endpoint
- [x] Implement a basic data action (e.g., GET `/data/recent`) using real data
- [x] Ensure it returns real data in a clear, structured format

### 4. OpenAPI Documentation
- [x] Confirm `/docs` and `/openapi.json` are accessible
- [x] Ensure endpoints and authentication requirements are documented

### 5. Environment/Config Management
- [x] Use environment variables for secrets/keys
- [x] Add .env file and python-dotenv for local development

### 6. End-to-End Test
- [x] Test the flow: ChatGPT → API (with auth) → Data action → Response
- [x] Confirm ChatGPT can "see" and use your API via OpenAPI schema

### 7. Documentation
- [x] Write and publish a user guide in docs/USER_GUIDE.md

### 8. Testing & User Experience
- [ ] Collect user feedback on ChatGPT Actions integration
- [ ] Test and refine prompt/response quality
- [ ] Improve error messages and guidance for common issues
- [ ] Add more helpful examples and onboarding tips

### 9. Migration to Message-Centric API Responses (Responses API Style)
- [ ] Design and add new response models (`Message`, `APIResponse`) in `core/models.py`
- [ ] Refactor all endpoints to return `APIResponse` with `messages`, `data`, and `code`
- [ ] Update error handling to use message-centric responses (except for 500/internal errors)
- [ ] Update OpenAPI schema and documentation to reflect new response format
- [ ] Refactor and expand tests for new response structure
- [ ] Test with ChatGPT Actions/LLM to ensure messages are surfaced as intended
- [ ] Refine user-facing messages for clarity and usefulness
- [ ] Remove legacy response models and code paths

**Note:**
- OpenAI deployment environment variables now use the convention:
  - `AZURE_COMPLETION_DEPLOYMENT_ID` for chat/completions
  - `AZURE_EMBEDDING_DEPLOYMENT_ID` for embeddings

## Architecture Design

### Core Components

1. **FastAPI Server**
   - Serves as the main interface for ChatGPT actions
   - Handles authentication and request validation
   - Routes requests to appropriate handlers
   - Provides OpenAPI documentation for ChatGPT integration

2. **Action Handlers**
   - Modular components for different types of operations
   - Each handler responsible for specific data operations
   - Implements error handling and response formatting
   - Maintains data consistency and validation

3. **Data Access Layer**
   - Abstracts data storage and retrieval operations
   - Implements caching where appropriate
   - Handles data transformation and formatting
   - Manages data security and access control

### Integration Flow

1. **ChatGPT Request Flow**
   ```
   ChatGPT -> Action Request -> FastAPI Server -> Action Handler -> Data Access -> Response
   ```

2. **Authentication Flow**
   ```
   ChatGPT -> Authentication Request -> JWT Token -> Authenticated Requests
   ```

## Implementation Phases

### Phase 1: Foundation (Current)
- [x] Set up project structure
- [x] Implement basic FastAPI server
- [x] Configure CORS and basic security
- [ ] Set up environment configuration
- [ ] Implement basic authentication
- [ ] Create OpenAPI documentation

### Phase 2: Structural & Feature Enhancements
- [ ] Refactor routes by capability:
  - `/msgraph/` (Outlook, OneDrive, Calendar)
  - `/data/` (CSV/SQL insights)
  - `/assist/` (LLM Q&A, summarization, analysis)
  - `/docs/` (file upload, document Q&A)
- [ ] Add `/docs/ask` endpoint for OneDrive-backed file Q&A
- [ ] Improve OpenAPI descriptions for ChatGPT function call UX
- [ ] **Checkpoint:** Discuss and possibly implement MCP (Microsoft Cloud Platform or other context-specific MCP)

### Phase 3: Core Actions
- [ ] Implement data retrieval actions
  - [ ] Get recent data
  - [ ] Search data
  - [ ] Filter data by criteria
- [ ] Implement data modification actions
  - [ ] Add new entries
  - [ ] Update existing entries
  - [ ] Delete entries
- [ ] Implement data analysis actions
  - [ ] Generate summaries
  - [ ] Create reports
  - [ ] Perform trend analysis

### Phase 4: Advanced Features
- [ ] Implement caching layer
- [ ] Add rate limiting
- [ ] Implement advanced search capabilities
- [ ] Add data validation and sanitization
- [ ] Implement error handling and logging
- [ ] Add monitoring and metrics

### Phase 5: Integration and Testing
- [ ] Create ChatGPT action schema
- [ ] Implement integration tests
- [ ] Perform security testing
- [ ] Load testing and optimization
- [ ] Documentation and examples

## Technical Requirements

### Dependencies
- FastAPI 0.104.1
- Uvicorn 0.24.0
- Python-dotenv 1.0.0
- Pydantic 2.4.2
- HTTPX 0.25.1
- Python-jose 3.3.0

### Development Environment
- Python 3.8+
- Virtual environment
- Git version control
- VS Code/Cursor IDE

## Security Considerations

1. **Authentication**
   - JWT-based authentication
   - API key management
   - Role-based access control

2. **Data Protection**
   - Input validation
   - Output sanitization
   - Rate limiting
   - CORS configuration

3. **Monitoring**
   - Request logging
   - Error tracking
   - Performance monitoring
   - Security audit logging

## Future Enhancements

1. **Scalability**
   - Implement caching strategies
   - Add load balancing
   - Optimize database queries
   - Implement connection pooling

2. **Features**
   - Real-time data updates
   - Batch processing
   - Advanced analytics
   - Custom action creation

3. **Integration**
   - Additional ChatGPT capabilities
   - Third-party service integration
   - Webhook support
   - Event-driven architecture

## Maintenance and Support

1. **Documentation**
   - API documentation
   - Integration guides
   - Troubleshooting guides
   - Development guidelines

2. **Monitoring**
   - Health checks
   - Performance metrics
   - Error tracking
   - Usage analytics

3. **Updates**
   - Regular security updates
   - Feature enhancements
   - Bug fixes
   - Dependency updates

## Timeline and Milestones

### Q2 2024
- Complete Phase 1
- Begin Phase 2 implementation
- Initial ChatGPT integration

### Q3 2024
- Complete Phase 2
- Begin Phase 3
- Beta testing with users

### Q4 2024
- Complete Phase 3
- Begin Phase 4
- Production deployment

## Notes and Considerations

1. **Data Privacy**
   - Ensure compliance with data protection regulations
   - Implement data encryption
   - Regular security audits

2. **Performance**
   - Optimize response times
   - Implement caching
   - Monitor resource usage

3. **Scalability**
   - Design for horizontal scaling
   - Implement load balancing
   - Optimize database access

4. **User Experience**
   - Clear error messages
   - Consistent response format
   - Comprehensive documentation

## Getting Started

1. **Setup**
   ```bash
   # Create virtual environment
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate

   # Install dependencies
   pip install -r requirements.txt

   # Create .env file
   cp .env.example .env
   ```

2. **Development**
   ```bash
   # Run development server
   python src/main.py

   # Run tests
   pytest
   ```

3. **Deployment**
   - Configure production environment
   - Set up monitoring
   - Implement CI/CD pipeline
   - Configure security settings 

1. Create Azure App Service
2. Enable GitHub Actions in Azure Portal
3. Configure these secrets in GitHub:
   - AZURE_CREDENTIALS
   - AZURE_APP_NAME
   - AZURE_WEBAPP_PUBLISH_PROFILE 