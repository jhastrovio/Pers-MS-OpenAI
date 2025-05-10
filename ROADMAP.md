# Personal MS Assistant – Unified Roadmap (Rev. 09 May 2025)

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

---

### 1. Core Orchestrator
- [ ] Intent classifier (email | drive | mixed)
- [ ] Response formatter with inline citations and confidence score
- [ ] Unit + integration tests (Mock‑Graph, httpx TestClient)

---

### 2. Retrieval via Responses API + File Search
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