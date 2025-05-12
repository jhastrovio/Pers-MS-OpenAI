Here’s your redrafted, clean and coherent markdown file:

---

# Custom GPT + Responses API via Tiny Proxy (No Front-End Code)

## Concept

Create a **Custom GPT** whose **Action** calls a **tiny proxy** that simply forwards to the **Responses API**.
This allows you to keep the native ChatGPT UI while accessing a larger vector store.

---

## How It Works

### 1️⃣ Tiny Proxy

Deploy a lightweight HTTPS endpoint (e.g., FastAPI, Cloudflare Worker, AWS Lambda) with:

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

Return the response as:

```json
{"answer": resp.output_text}
```

---

### 2️⃣ Custom GPT Action

Describe the `/rag` endpoint in your OpenAPI schema:

```yaml
/rag:
  post:
    operationId: rag
    requestBody:
      content:
        application/json:
          schema:
            type: object
            properties:
              prompt:
                type: string
              filters:
                type: object
    responses:
      "200":
        content:
          application/json:
            schema:
              properties:
                answer:
                  type: string
```

Refer to [BYU’s guide on GPT Action schemas](https://platform.openai.com/docs/guides/gpt/custom-actions).

---

### 3️⃣ GPT Instructions

Instruct your GPT:

> “When the user asks about Outlook emails or OneDrive docs, call `/rag` with their prompt.”

---

## ✅ Pros

| What You Gain        | Why                                                             |
| -------------------- | --------------------------------------------------------------- |
| Zero front-end code  | Users stay inside ChatGPT; no external UI needed                |
| Single retrieval hop | Proxy forwards to Responses API and handles file\_search        |
| Future-proof         | Easily swap models, vector stores, or add rerank logic in proxy |

---

## ❌ Cons and Mitigations

| Limitation                               | Mitigation                                                    |
| ---------------------------------------- | ------------------------------------------------------------- |
| Extra network hop (GPT ➜ proxy ➜ OpenAI) | Keep proxy and OpenAI in same region; payloads are small      |
| Proxy key & auth maintenance             | Store `OPENAI_API_KEY` as env var; use API key header         |
| 10k file / 5M token vector store cap     | Acceptable for your use; scale to external DB later if needed |

---

## 🔗 Quick Start Links

* [File Search + Vector Store Docs](https://platform.openai.com/docs/guides/file-search)
* [Custom GPT Actions + OpenAPI Guide](https://platform.openai.com/docs/guides/gpt/custom-actions)

---

## 🚀 Summary

Set up the proxy in an afternoon, paste the schema into Actions, and instantly have a **ChatGPT-native RAG bot** with **no UI coding**.

