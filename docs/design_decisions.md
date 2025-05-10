
# Personal MS Chatgpt - Design Decisions

Version: 10 May 2025

---

## 🎯 Purpose

This document records key design decisions made for the Personal MS Chatgpt project. It explains architectural and technology choices to help future maintainers understand the rationale.

---

## ✅ Core Design Principles

* **Simplicity first**: Minimal viable components with strong modularity.
* **Scalable path**: Start small (OpenAI File Search), plan for scale-out (Azure AI Search).
* **AI-native workflow**: Leverage Cursor + ChatGPT for accelerated development.
* **Security by design**: OAuth2 + API key fallback + Purview + OWASP ASVS.

---

## 📐 Major Decisions

### 1️⃣ FastAPI as backend orchestrator

* Chosen for high performance, async support, and developer-friendly ecosystem.
* Natural fit with modern Python tooling.

### 2️⃣ OpenAI `responses.create()` as primary LLM endpoint

* New standard API in OpenAI Python v1.x library.
* Fully supports file\_search tool + streaming + async.
* Future-proof vs. older `chat.completions.create()` endpoint.

### 3️⃣ Use of OpenAI File Search initially

* Fully managed vector store with zero ops burden.
* 10,000 file limit suits Phase 1 + Phase 2 data sizes.
* Direct integration with Responses API = simplest RAG flow.

### 4️⃣ Planned scale-out to Azure AI Search

* Trigger conditions: file count > 10,000 OR >300 queries/day average.
* Azure AI Search offers hybrid BM25 + vector search + ACL trimming.
* Reindex + swap `vector_store_ids` → zero downtime migration.

### 5️⃣ MSAL (Microsoft Authentication Library) for OAuth2

* Enables secure service principal flow for backend automation.
* Already proven in enterprise Azure + Graph integrations.

### 6️⃣ Application Insights for observability

* Provides full backend tracing, latency dashboards, usage alerts.
* No external monitoring system required.

### 7️⃣ Live sync design via Azure Function

* Graph delta queries every 5 minutes.
* Automates file ingestion updates for any mailbox or document changes.
* Keeps OpenAI File Search vector store always fresh.

### 8️⃣ ChatGPT Actions as client interface

* Provides secure + managed gateway for users to query internal knowledge base.
* Company Assistant will be published with file\_search attached.
* Allows front-end inline citations (filename • page) + confidence score.

---

## ❗ Rejected Alternatives

| Option                           | Reason for Rejection                                    |
| -------------------------------- | ------------------------------------------------------- |
| LangChain as full orchestrator   | Added unnecessary complexity for this focused use case. |
| LlamaIndex as ingestion pipeline | Lighter in functionality vs. Azure + native scripts.    |
| Vector DBs (Pinecone, Qdrant)    | Avoid additional hosting & ops at MVP phase.            |

---

## 📝 Conclusion

The current stack maximizes developer velocity, minimizes unnecessary complexity, and provides a clear growth path for scale + security + observability. It remains intentionally small & tightly scoped.

---

Last updated: 10 May 2025
