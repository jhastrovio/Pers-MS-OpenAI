# API Examples

_All LLM/AI (RAG, chat, file_search, etc.) is accessed via OpenAI (openai Python SDK, Responses API). Azure is not used for LLM/AI—only for Microsoft Graph and related infrastructure._

_This document will track open and completed action items for the Pers MS Open AI project._ # Pers MS Open AI – API Examples

Version: 10 May 2025

---

## 🎯 Purpose

This document provides reference code snippets for using the OpenAI Python SDK + Responses API within the Personal MS ChatGPT project.

---

## ✅ Setup

```bash
pip install openai
```

Add your API key to `.env` or environment variable:

```bash
OPENAI_API_KEY=your-key-here
```

---

## 📝 Basic `responses.create()` example

```python
from openai import OpenAI

client = OpenAI()

response = client.responses.create(
    model="gpt-4o",
    input="Explain the concept of Retrieval-Augmented Generation (RAG)."
)
print(response.output_text)
```

---

## 🔄 Chat with file\_search attached

```python
response = client.responses.create(
    model="gpt-4o",
    instructions="You are a corporate assistant using file_search.",
    tools=[{"type": "file_search"}],
    input="Summarise the document about the company travel policy."
)
print(response.output_text)
```

---

## 🎥 Streaming responses

```python
stream = client.responses.create(
    model="gpt-4o",
    input="Write a short bedtime story about a unicorn.",
    stream=True
)
for event in stream:
    print(event)
```

---

## ⚡ Async example

```python
import asyncio
from openai import AsyncOpenAI

client = AsyncOpenAI()

async def main():
    response = await client.responses.create(
        model="gpt-4o",
        input="Give me 3 key facts about Microsoft Graph API."
    )
    print(response.output_text)

asyncio.run(main())
```

---

## 🖼️ Vision + Text input

```python
img_url = "https://upload.wikimedia.org/wikipedia/commons/d/d5/2023_06_08_Raccoon1.jpg"
prompt = "What is in this image?"

response = client.responses.create(
    model="gpt-4o-mini",
    input=[
        {
            "role": "user",
            "content": [
                {"type": "input_text", "text": prompt},
                {"type": "input_image", "image_url": img_url}
            ]
        }
    ]
)
print(response)
```

---

## 💡 Tips

* Prefer `AsyncOpenAI()` in production to maximize concurrency.
* Use `stream=True` for large completions to minimize latency.
* Always use structured exception handling for robust error handling.

---

Last updated: 10 May 2025
