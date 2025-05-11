import pytest
import asyncio
from httpx import AsyncClient
from unittest.mock import patch
from app import app
import os
from dotenv import load_dotenv
load_dotenv()

@pytest.mark.asyncio
async def test_search_endpoint(monkeypatch):
    # Mock OpenAIService.search_data or any downstream LLM/AI call
    mock_results = {
        "results": [],
        "total_count": 0,
        "page": 1,
        "page_size": 10
    }
    api_key = os.environ["P_Deploy_API_Key"]
    headers = {"X-API-Key": api_key}
    # Patch DataAccess.search_data to return mock results
    with patch("core.data_access.DataAccess.search_data", return_value=mock_results):
        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.post("/data/search", json={"query": "test"}, headers=headers)
            assert response.status_code == 200
            data = response.json()
            assert "data" in data
            assert "messages" in data

@pytest.mark.llm
@pytest.mark.asyncio
async def test_search_real_data():
    api_key = os.environ["P_Deploy_API_Key"]
    headers = {"X-API-Key": api_key}
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post("/data/search", json={"query": "Q2 report"}, headers=headers)
        assert response.status_code == 200
        data = response.json()
        print(data)  # For manual inspection
        assert "data" in data

@pytest.mark.asyncio
async def test_answer_endpoint():
    api_key = os.environ["P_Deploy_API_Key"]
    headers = {"X-API-Key": api_key}
    mock_answer = {"answer": "This is a mock answer."}
    with patch("core.data_access.DataAccess.answer_question", return_value=mock_answer):
        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.post(
                "/data/answer",
                json={"question": "What is the answer?", "context_ids": ["id1"]},
                headers=headers
            )
            assert response.status_code == 200
            data = response.json()
            assert "data" in data
            assert "messages" in data

@pytest.mark.asyncio
async def test_recent_endpoint():
    api_key = os.environ["P_Deploy_API_Key"]
    headers = {"X-API-Key": api_key}
    mock_entries = []
    with patch("core.data_access.DataAccess.get_recent_data", return_value=mock_entries):
        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.get("/data/recent", headers=headers)
            assert response.status_code == 200
            assert isinstance(response.json(), list) 