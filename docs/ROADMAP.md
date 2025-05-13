# Pers MS Open AI – Unified Roadmap  
**Revision 13 May 2025**

> One file = one source of truth.  
> Design rationale lives in `design_decisions_clean.md` (ADR v1.5).

---

## 🎯 Goal
Operate a ChatGPT-native assistant that can search & summarise Outlook e-mails and OneDrive documents, with a clear scale-out path (>10 k files) and enterprise-grade security.

---

## 0. Foundation — **Delivered**
- [x] Git repo, GitHub Actions CI, pre-commit hooks  
- [x] FastAPI skeleton (`/health`, `/rag`) with MSAL middleware  
- [x] Application Insights wired to **dev** & **prod** App Services  
- [x] OpenAI SDKs (`openai`, `openai-agents`) centralised in `OpenAIService`  

---

## 1. Core Orchestrator — **Delivered**
- [x] Intent classifier (`email | drive | mixed | data`)  
- [x] Response formatter (inline citations + confidence)  
- [x] Unit & integration tests (httpx TestClient + mock Graph)  

---

## 2. Retrieval via Responses API + File Search — **Delivered / Ongoing**
- [x] `corp-kb` vector-store (GA endpoint)  
- [x] Unified ingestion (e-mails / attachments / OneDrive docs → JSONL → vector-store)  
- [x] Tiny proxy calls `responses.create()` with `file_search`  
- [ ] **Metadata filters:**  move DataAccess.search_data to openai_service.retrieve; ensure proxy re-uses that wrapper; add smoke tests.

---

## 3. ChatGPT Action & UX — **Future Work**
*(Option A – keep users inside ChatGPT)*  
- [ ] Publish **Company-Assistant** Custom GPT (prod vector_store_id)  
- [ ] Citation badges: `filename • page` in answers  
- [ ] Latency & precision dashboards in Application Insights  

---

## 4. Live Sync & Budget Control — **Future Work**
- [ ] Azure Function (5-min cron) — Graph delta sync → re-ingest changed blobs  
- [ ] Retrieval wrapper: “**top-k → refine**” with fallback when `score < 0.15`  
- [ ] Alerts: `file_count ≥ 9 500` **OR** daily spend > US$ 5  

---

## 5. Security & Compliance Hardening — **Future Work**
- [ ] **Azure Key Vault** for secrets + 90-day rotation *(paused, tracked)* ← ADR-007  
- [ ] OWASP ASVS threat-model workshop  
- [ ] Purview scan → redact PII before upload  
- [ ] Audit logs exported to Log Analytics  

---

## 6. Scale-out Path (>10 k files) — **Future Work**
Trigger: `file_count > 10 000` **OR** `avg_daily_queries > 300`  
- [ ] Evaluate **Azure AI Search** (hybrid BM25 + vector + ACLs)  
- [ ] Re-index & switch `vector_store_ids` with zero downtime  

---

## 📊 Acceptance Criteria
| KPI                            | Target  |
|--------------------------------|---------|
| End-to-end latency (P95)       | ≤ 4 s   |
| Answer precision (manual)      | ≥ 80 %  |
| Cost per 100 queries           | < US$ 5 |
| Vector-store file cap          | ≤ 10 000|
| Security incidents             | 0       |

---

*Last updated 13 May 2025 — consistent with ADR v1.5.*
