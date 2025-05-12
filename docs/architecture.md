# System Architecture

# Pers MS Open AI - Architecture

Version: 10 May 2025

---

## 🎯 Overview

The Pers MS Open AI is a scalable, future-proof AI assistant that integrates Outlook emails and OneDrive documents into a ChatGPT experience. All LLM/AI (RAG, chat, file_search, etc.) is accessed via OpenAI (openai Python SDK, Responses API). Azure is only used for Microsoft Graph, Key Vault, and monitoring—not for LLM/AI.

**All LLM/AI and embedding calls must go through the OpenAIService class (`openai_service` instance) for consistency. Do not use direct OpenAI API calls elsewhere in the codebase.**

This document defines the system architecture.

---

## 🧩 High-Level Architecture

```
[ChatGPT Action / Web Client]
            ↓
[FastAPI Orchestrator Backend]
    → MSAL OAuth, Intent Classifier
    → Data Ingest Pipelines
    → OpenAI Responses API + file_search
    → Post-processing: Citations + Confidence
            ↓
[OpenAI File Search (10k file limit)]
            ↓
[Future: Azure AI Search (>10k files or 300+ queries/day)]
```

---

## 📦 Component Breakdown

### 1️⃣ FastAPI Orchestrator

* Main API entry point (`/query` endpoint)
* MSAL OAuth2 middleware for authentication
* Routes requests to appropriate handler modules
* Logs metrics to Application Insights

### 2️⃣ Intent Classifier

* Classifies user intent: `email`, `drive`, or `mixed`
* Enables targeted retrieval pipeline execution

### 3️⃣ Data Ingest Pipelines

* `graph_ingest.py`: Outlook Graph API → JSONL converter (one email per line/object, with metadata, body, and attachment references)
* `onedrive_ingest.py`: OneDrive watcher → document and attachment upload
* `ingest.py`: Unified file upload to OpenAI File Search with polling
* **All uploads (emails, attachments, docs) use the OpenAI SDK GA Vector Store endpoints, attaching metadata via the `attributes` field.**
* **REST API workarounds are no longer required.**
* **Metadata-based search and filtering is supported; check OpenAI docs for latest filter syntax.**
* Attachments are stored in OneDrive and referenced in the email JSONL by file ID or URL. Attachments are also uploaded to File Search as separate files, with metadata linking them to their parent email.

### 4️⃣ OpenAI Responses API Layer

* `chat_handler.py`: Connects to OpenAI via `responses.create()`
* file\_search tool attached for document retrieval
* Handles streaming + async completions where needed

### 5️⃣ Post-Processing & Formatting

* `response_formatter.py`: Adds inline citations (filename + page)
* Attaches confidence scores to response text

### 6️⃣ Azure Functions (Live Sync)

* Runs 5-min cron jobs to check Graph delta changes
* Triggers re-ingest for any changed bundles

### 7️⃣ Monitoring + Budget Alerts

* Application Insights: latency, precision dashboards
* Trigger alerts when file count nears 9,500 or usage spikes

---

## 🪜 Scaling Path

| Trigger                        | Action                                              |
| ------------------------------ | --------------------------------------------------- |
| file\_count > 10,000           | Reindex into Azure AI Search (hybrid BM25 + vector) |
| > 300 queries/day avg          | Same as above                                       |
| Swap action vector\_store\_ids | Zero downtime transition                            |

---

## 🔐 Security Considerations

* MSAL OAuth2 flow (service principal)
* JWT + API Key authentication fallback
* Key Vault rotation pipeline (90-day)
* Purview PII redaction on document ingestion
* OWASP ASVS security review

---

## 📝 Notes

* file\_search tool (OpenAI-managed vector index, 10k file limit)
* Azure AI Search provides hybrid BM25 + vector retrieval beyond file\_search scale

---

Last updated: 10 May 2025
