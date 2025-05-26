import asyncio
from core.openai_1_5_0.main import OpenAIClient


def test_stream_response():
    client = OpenAIClient()

    async def generator():
        for chunk in [
            {"choices": [{"delta": {"content": "Hello "}}]},
            {"choices": [{"delta": {"content": "world"}}]},
        ]:
            yield chunk

    collected = []

    async def run():
        async for part in client.stream_response(generator()):
            collected.append(part)

    asyncio.run(run())

    assert collected == ["Hello ", "world"]


def test_apply_filters():
    client = OpenAIClient()
    query = {"query": "test"}
    filters = {"author": "alice"}

    result = client.apply_filters(query, filters)

    assert query == {"query": "test"}  # original not modified
    assert result["filter"]["author"] == "alice"
