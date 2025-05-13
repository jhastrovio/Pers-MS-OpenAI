# Pers MS OpenAI – Architectural Decision Record (ADR Log)

Version: 1.5 – 13 May 2025

---

## 🎯 Purpose

Maintain a concise, version‑controlled trail of **architectural decisions only**. Delivery status & future work sit in `ROADMAP.md`.

---

## 📑 Index

| ID      | Title                                                        | Status    | Date        |
| ------- | ------------------------------------------------------------ | --------- | ----------- |
| ADR‑001 | FastAPI as backend orchestrator                              | Accepted  | 10 May 2025 |
| ADR‑002 | OpenAI SDKs as primary LLM & Agent endpoints                 | Accepted  | 10 May 2025 |
| ADR‑003 | Email & attachment ingestion via JSONL → Vector Store        | Accepted  | 10 May 2025 |
| ADR‑004 | Structured JSON response schema for answers                  | Accepted  | 10 May 2025 |
| ADR‑005 | OpenAI Vector Store for Phase 1–2 storage                    | Accepted  | 10 May 2025 |
| ADR‑006 | Custom GPT Action → Tiny Proxy → Responses API & File Search | Accepted  | 13 May 2025 |
| ADR‑007 | Microsoft Authentication Library (MSAL) for OAuth2           | Proposed  | –           |
| ADR‑008 | Azure Application Insights for observability                 | Proposed  | –           |
| ADR‑009 | Catalogue of rejected alternatives                           | Catalogue | 13 May 2025 |

---

### ADR‑001 FastAPI as backend orchestrator

**Status:** Accepted – 10 May 2025
Need async, high‑performance Python API; chose FastAPI for `/rag`, health, and future endpoints.

---

### ADR‑002 OpenAI SDKs as primary LLM & Agent endpoints

**Status:** Accepted – 10 May 2025
Use `openai` and `openai‑agents` exclusively for chat/RAG; no raw REST calls.

---

### ADR‑003 Email & attachment ingestion via JSONL → Vector Store

**Status:** Accepted – 10 May 2025
Serialise emails to JSONL; ingest attachments separately with metadata links.

---

### ADR‑004 Structured JSON response schema for answers

**Status:** Accepted – 10 May 2025
All answers return `{ answer, citations[], confidence }` before rendering.

---

### ADR‑005 OpenAI Vector Store for Phase 1–2 storage

**Status:** Accepted – 10 May 2025
Up to 10 k docs; supports native metadata filters. Migrate when cap or cost exceeded (tracked in `ROADMAP.md`).

---

### ADR‑006 Custom GPT Action → Tiny Proxy → Responses API & File Search

**Status:** Accepted – 13 May 2025

#### Context

We want users to stay inside the familiar ChatGPT UI **and** tap the full GA Retrieval feature‑set (metadata filters, streaming). ChatGPT *Actions* allow a Custom GPT to invoke an external HTTPS endpoint—our tiny proxy—so we can forward the request to `responses.create()` which supports metadata filters.

#### Decision

Build a private **Custom GPT** with one Action `/rag` that calls a **tiny proxy** (FastAPI in Azure Container App or Cloudflare Worker). The proxy translates the payload into a single SDK call:

```python
client.responses.create(
    model="gpt-4o",
    input=req.json["prompt"],
    tools=[{
        "type": "file_search",
        "vector_store_ids": [VS_ID],
        "file_search": {"filters": req.json.get("filters", {})}
    }]
)
```

Proxy returns `{ "answer": resp.output_text }`.

#### End‑to‑End Picture (Who / What / When)

| Step | Actor / Layer       | What happens                                                |
| ---- | ------------------- | ----------------------------------------------------------- |
| 1    | **User in ChatGPT** | Types a question.                                           |
| 2    | **Custom GPT**      | Detects question needs Action, calls `/rag`.                |
| 3    | **Tiny Proxy**      | Builds `responses.create()` call (adds metadata `filters`). |
| 4    | **Responses API**   | Searches Vector Store, streams answer back.                 |
| 5    | **Tiny Proxy**      | Extracts `output_text`, returns JSON.                       |
| 6    | **Custom GPT**      | Renders answer to user.                                     |

Latencies: ChatGPT→Proxy (≈200 ms regional), Proxy→OpenAI (≈100 ms). Target P95 ≤ 4 s remains.

#### Consequences

* ✅ **Zero front‑end code** – users stay in ChatGPT.
* ✅ **Full GA features** (metadata, streaming, JSON mode) because proxy uses latest SDK.
* ✅ **Extensible** – future rerankers or hybrid search can be added inside proxy.
* ❌ **Extra hop** adds small latency—mitigated by regional co‑location.
* ❌ **Secrets** live in proxy; Key Vault integration scheduled (ADR‑007).

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
| LlamaIndex pipeline                         | Missing advanced metadata support                |
| Self‑hosted vector DB (Pinecone, Qdrant)    | Adds ops overhead at MVP                         |

---

## 🗒️ Changelog

* **v1.5 – 13 May 2025** – Re‑aligned with Option A: ADR‑006 accepted; removed ADR‑010; added end‑to‑end flow & consequences.
* **v1.4 – 13 May 2025** – (superseded) temporary pivot to direct Responses API.
