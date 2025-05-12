# Pers MS Open AI – Unified Roadmap (Rev. 09 May 2025)

## Related Documentation
- [System Architecture](docs/architecture.md)
- [Design Decisions](docs/design_decisions.md)
- [Action Items](docs/action_items.md)

> For all major design or technology changes, update `docs/design_decisions.md` to keep rationale in sync with the roadmap.

> Ongoing and open tasks are tracked in [docs/action_items.md](docs/action_items.md) or via GitHub Issues/project boards.

## Goal
Operate a single ChatGPT assistant that searches & summarises Outlook e‑mails and OneDrive documents. The design must scale to larger data volumes and future task‑specific offshoots without re‑architecting.

---

### 0. Foundation (Complete, except Key Vault)
- [x] Repository, GitHub Actions CI, pre‑commit hooks
- [x] FastAPI skeleton (/health, /query) with MSAL OAuth (service‑principal) middleware
- [ ] Secrets in Azure Key Vault (**deferred**)
- [x] Application Insights attached to both dev & prod App Services
- [x] All LLM/AI (vector store, retrieval, chat, etc.) use OpenAI (openai Python SDK, Responses API). No Azure OpenAI is used; Azure is only for Microsoft Graph, Key Vault, and monitoring.
- [x] **All LLM/AI and embedding calls must go through the OpenAIService class (`openai_service` instance) for consistency. Do not use direct OpenAI API calls elsewhere in the codebase.**

---

### 1. Core Orchestrator
- [x] Intent classifier (email | drive | mixed | data) — implemented, tested, ongoing data/model improvement (to be reviewed for OpenAI SDK compatibility)
- [x] Response formatter with inline citations and confidence score — implemented and tested (to be reviewed for OpenAI SDK compatibility)
- [x] Unit tests for intent classifier and response formatter (to be reviewed for OpenAI SDK compatibility)
- [x] Integration tests (Mock‑Graph, httpx TestClient, real LLM/AI, PDF processing)
- [x] **Review and refactor all orchestrator logic, tests, and dependencies to ensure full compatibility with OpenAI Responses SDK and Agents SDK.**
- [x] Remove any Azure OpenAI-specific code, configs, or mocks if present.
- [x] **All LLM/AI integration and PDF processing are now fully migrated and tested with OpenAIService and pypdf.**

---

### 2. Retrieval via Responses API + File Search
- [x] Create a single vector‑store (corp-kb, unlimited expiry)
- [x] Minimal upload pipeline tested and working with OpenAI SDK GA Vector Store endpoints and metadata (attributes)
- [x] Converter scripts (prototype)
- [x] Outlook Graph delta → monthly .jsonl bundles (strip signatures)
- [x] OneDrive watcher → direct pass‑through of PDFs/Docs
- [x] ingest.py upload script – idempotent; polls status until completed
- [x] **All ingestion and retrieval scripts now use the OpenAI SDK GA Vector Store endpoints and support metadata via the `attributes` field.**
- [x] **Unified ingestion: All emails, attachments, and OneDrive docs are now processed through a single pipeline and uploaded to the OpenAI vector store with consistent metadata.**
- [x] **UX layer implemented via Custom GPT in ChatGPT, using Actions to call a tiny proxy that forwards to the OpenAI Responses API. No custom web front-end required.**
- [ ] **Implement and test metadata-based search and filtering as OpenAI updates documentation/examples.**
- [ ] **Future UX improvements will focus on prompt engineering, Action schema, and proxy enhancements.**
- [x] **Email ingestion:**
    - [x] Fetch emails via Graph API, save as JSONL (one email per line/object, with metadata and body).
    - [x] For each email, include a list of attachment references (OneDrive file IDs/URLs) in the JSONL.
    - [x] Store all attachments in OneDrive; process all files (including attachments) through the unified OneDrive ingestion pipeline.
    - [x] Automate the full pipeline for new/changed emails and attachments.

---

### 3. Live Sync & Budget Control
- [ ] Azure Function (5‑min cron) runs Graph delta sync, re‑uploads changed bundles
- [ ] "Top‑k + refine" retrieval wrapper (1 k tokens, fallback fetch on low confidence)
- [ ] Alerts: vector_store.file_count ≥ 9 500, spikes in usage.vector_store_bytes
- [ ] **Ensure retrieval wrappers and alerts are compatible with OpenAI SDKs.**

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