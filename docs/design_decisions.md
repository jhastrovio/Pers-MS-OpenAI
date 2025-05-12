# Pers MS Open AI - Design Decisions

Version: 10 May 2025

---

## 🎯 Purpose

This document records key design decisions made for the Pers MS Open AI project. It explains architectural and technology choices to help future maintainers understand the rationale.

---

## 🚀 OpenAI SDK Usage (2025+)

- **All LLM/AI (chat, RAG, file_search, etc.) is accessed via the official OpenAI Responses SDK (`openai` ≥ 1.14).**
- **Multi-step agent orchestration and complex workflows use the OpenAI Agents SDK (`openai-agents` ≥ 0.3).**
- **All file and metadata uploads use the OpenAI Vector Store API (GA endpoints) via the Python SDK, using the `attributes` field for metadata.**
- **REST API workarounds are no longer needed; all ingestion is handled via the SDK.**
- **Metadata filtering and search are supported; check the latest OpenAI documentation for filter syntax and updates.**
- **All LLM/AI and embedding calls must go through the OpenAIService class (`openai_service` instance) for consistency. Do not use direct OpenAI API calls elsewhere in the codebase.**
- **Version pinning:** Both SDKs are pinned in `requirements.txt` as per project rules.
- **Secrets:** API keys are never committed; always loaded from `.env` or the Cursor Secrets tab.
- **Reference:** See [OpenAI Responses SDK.md](docs/OpenAI Responses SDK.md) and [OpenAI Agents SDK.md](docs/OpenAI Agents SDK.md) for quick-starts and conventions.

---

## ✅ Core Design Principles

* **Simplicity first**: Minimal viable components with strong modularity.
* **Scalable path**: Start small (OpenAI File Search), plan for scale-out (Azure AI Search).
* **AI-native workflow**: Leverage Cursor + ChatGPT for accelerated development. All LLM/AI (RAG, chat, file_search, etc.) is accessed via the official OpenAI SDKs. Azure is only used for Microsoft Graph, Key Vault, and monitoring—not for LLM/AI. All LLM/AI code must use the official OpenAI SDKs.
* **Security by design**: OAuth2 + API key fallback + Purview + OWASP ASVS.

---

## 📐 Major Decisions

### 1️⃣ FastAPI as backend orchestrator

* Chosen for high performance, async support, and developer-friendly ecosystem.
* Natural fit with modern Python tooling.

### 2️⃣ OpenAI SDKs as primary LLM/Agent endpoints

* All LLM/AI calls use the OpenAI Responses SDK (`openai.responses.create`).
* Multi-step agent orchestration uses the OpenAI Agents SDK (`openai-agents`).
* Fully supports file_search tool, streaming, async, and agent workflows.
* No Azure OpenAI is used; all LLM/AI is accessed via OpenAI endpoints and SDKs.

### 3️⃣ Use of OpenAI File Search initially

* Fully managed vector store with zero ops burden.
* 10,000 file limit suits Phase 1 + Phase 2 data sizes.
* Direct integration with Responses API = simplest RAG flow.
* **All file and document uploads (including emails, attachments, and OneDrive docs) are performed via the OpenAI Vector Store API (GA endpoints), which supports metadata for each file via the `attributes` field.**
* **Metadata is required and attached to every file/document for robust search and filtering. Filtering is supported; check OpenAI docs for latest filter syntax.**

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
* Company Assistant will be published with file_search attached.
* Allows front-end inline citations (filename • page) + confidence score.

### 9️⃣ Email and Attachment Ingestion

* All emails are ingested as JSONL files (one email per line/object) for efficient, scalable processing and OpenAI File Search compatibility.
* Each email JSON object includes metadata (subject, sender, recipients, date, etc.), body, and a list of references to attachment files.
* Attachments are stored in OneDrive for centralized, secure storage. Each attachment is referenced in the email JSONL by its OneDrive file ID or URL.
* Attachments are also ingested into OpenAI File Search as separate files, with metadata linking them to their parent email.
* **All uploads to OpenAI File Search are performed using the GA Vector Store SDK endpoints, with metadata attached to each file for advanced filtering and retrieval. REST API workarounds are no longer required.**

---

## 📦 Response Formatting and Output

- **Structured JSON Output:**  
  All LLM and orchestrator responses use a structured JSON format with three fields:  
  - `answer` (str): The main response or summary.  
  - `citations` (list of dict): Source references, with type-specific fields (e.g., file/page for drive, subject for email, table for data).  
  - `confidence` (float, optional): Model confidence score.

- **Citation Formatting:**  
  Citations are formatted based on their type for clarity:
  - Drive: `filename, p.X (drive)`
  - Email: `Email: subject (Outlook)`
  - Data: `Table: table_name (data)`

- **Plain Text Conversion Utility:**  
  A utility function converts the JSON response to a user-friendly plain text string, combining the answer, formatted citations, and confidence score.

- **Rationale:**  
  This approach ensures responses are both machine-readable (for ChatGPT Actions and integrations) and human-readable (for direct user display). It also supports future extensibility for new source types.

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
