# Pers MS OpenAI – Architectural Decision Record (ADR Log)

Version: 1.6 – 14 May 2025

---

## 🎯 Purpose

Track architecture **decisions** and the single authoritative **system overview** in one document. Delivery status & future work sit in `ROADMAP.md`.

---

## 📥 Enterprise RAG Ingestion Architecture (System Overview)

The platform ingests emails, attachments, and documents from Microsoft Graph and OneDrive, cleans and enriches them with structured *attributes*, and stores all content centrally in OneDrive as the master data lake. Raw `.eml` files are kept for audit while cleaned emails, attachments, and documents are saved as structured `.json` files. A batch process combines all cleaned records into a single JSONL file for upload to the OpenAI vector store, enabling semantic search and attribute‑filtered retrieval via the Responses API. OneDrive remains the immutable source of truth, allowing full re‑ingestion or re‑indexing when needed.

```
                📌 Microsoft Graph
                📅 - Emails + attachments
                📅 - OneDrive documents
                                 ↓
                       [ Data Extractor ]
                                 ↓
                📅 OneDrive Root
                                 ↓
 Emails
 - Save raw email → /emails/raw/{message_id}.eml
 - Clean + enrich email → /emails/cleaned/{message_id}.json
                                 ↓
 Attachments
 - Extract attachments from email MIME parts
 - Extract attachment text
 - Create JSON + add `parent_email_id`
 - Save → /emails/attachments/{attachment_id}.json
                                 ↓
 Documents (OneDrive)
 - Extract text
 - Create cleaned JSON
 - Save → /documents/cleaned/{file_id}.json
                                 ↓
                       [ Ingestion Pipeline ]
                                 ↓
 Combine all JSON records → create single batch JSONL
                                 ↓
        OpenAI Vector Store Upload
        - Store embeddings + attributes for RAG retrieval
                                 ↓
Semantic & attribute‑filtered retrieval via Responses API
```

> **Update flow:** After initial load, new or modified items in OneDrive are detected and added to incremental JSONL batches for upload. Periodic full re‑ingestion can be used for deletions or schema changes.

---

## 📑 ADR Index

| ID      | Title                                                        | Status    | Date        |
| ------- | ------------------------------------------------------------ | --------- | ----------- |
| ADR‑001 | FastAPI as backend orchestrator                              | Accepted  | 10 May 2025 |
| ADR‑002 | OpenAI SDKs as primary LLM & Agent endpoints                 | Accepted  | 10 May 2025 |
| ADR‑003 | Email / Doc ingestion → OneDrive → JSONL → Vector Store      | Accepted  | 14 May 2025 |
| ADR‑004 | Structured JSON **attributes** schema for answers            | Accepted  | 10 May 2025 |
| ADR‑005 | OpenAI Vector Store for Phase 1–2 storage                    | Accepted  | 10 May 2025 |
| ADR‑006 | Custom GPT Action → Tiny Proxy → Responses API & File Search | Accepted  | 13 May 2025 |
| ADR‑007 | Microsoft Authentication Library (MSAL) for OAuth2           | Proposed  | –           |
| ADR‑008 | Azure Application Insights for observability                 | Proposed  | –           |
| ADR‑009 | Catalogue of rejected alternatives                           | Catalogue | 13 May 2025 |

---

### ADR‑001 FastAPI as backend orchestrator

**Status:** Accepted – 10 May 2025
Need async, high‑performance Python API; chose FastAPI for `/rag`, health, and future endpoints.

---

### ADR‑002 OpenAI SDKs as primary LLM & Agent endpoints

**Status:** Accepted – 10 May 2025
Use `openai` and `openai‑agents` exclusively for chat/RAG; no raw REST calls.

---

### ADR‑003 Email / Doc ingestion → OneDrive → JSONL → Vector Store

**Status:** Accepted – 14 May 2025
*Context* – We ingest heterogeneous corp data (emails, attachments, docs) and require consistent retrieval via attributes filters.
*Decision* – Save raw `.eml` plus cleaned `.json` (emails, attachments) and cleaned document JSON in OneDrive. Batch combine all cleaned records into a JSONL file; upload to OpenAI vector store. Each record follows the schema `{"text": "…", "attributes": {...}}` using the attributes list defined in Architecture Overview.
*Consequences* – OneDrive is single source‑of‑truth; vector store is append‑only; incremental updates handled via daily delta batches.

---

### ADR‑004 Structured JSON **attributes** schema for answers

**Status:** Accepted – 10 May 2025
All system answers adopt `{ answer, citations[], confidence }`; ingestion records use flat primitive **attributes** to allow filters (`author`, `sent_at`, etc.).

---

### ADR‑005 OpenAI Vector Store for Phase 1–2 storage

**Status:** Accepted – 10 May 2025
Store up to 10 k docs; supports native attribute filters. Migrate when cap or cost exceeded (tracked in `ROADMAP.md`).

---

### ADR‑006 Custom GPT Action → Tiny Proxy → Responses API & File Search

**Status:** Accepted – 13 May 2025

**Code pattern (updated):**

```python
client.responses.create(
    model="gpt-4o",
    input=req.json["prompt"],
    tools=[{
        "type": "file_search",
        "vector_store_ids": [VS_ID],
        "filters": req.json.get("filters", {})
    }]
)
```

— users remain in ChatGPT; proxy uses GA features (`filters`, streaming).

---

### ADR‑007 Microsoft Authentication Library (MSAL) for OAuth2

**Status:** Proposed
Plan to adopt MSAL client‑credential flow for Graph & Key Vault access.

---

### ADR‑008 Azure Application Insights for observability

**Status:** Proposed
Add distributed tracing & metrics; alert on latency & errors.

---

### ADR‑009 Rejected alternatives (catalogue)

| Option                                      | Reason                                           |
| ------------------------------------------- | ------------------------------------------------ |
| Direct UI (Teams bot / web) + Responses API | Adds front‑end build; user loses ChatGPT context |
| LangChain orchestrator                      | Too heavy for scoped use                         |
| LlamaIndex pipeline                         | Missing advanced attribute support               |
| Self‑hosted vector DB (Pinecone, Qdrant)    | Adds ops overhead at MVP                         |

---

## 🗒️ Changelog

* **v1.6 – 14 May 2025** – Merged system overview + ingestion diagram into ADR doc; expanded ADR‑003; corrected filters snippet in ADR‑006; unified terminology to **attributes**.
* **v1.5 – 13 May 2025** – Option A realignment.
