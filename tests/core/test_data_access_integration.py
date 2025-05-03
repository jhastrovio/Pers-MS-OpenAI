import pytest
import os
from datetime import datetime, timedelta
from src.core.models import DataSource, SearchQuery, OutlookEmail, OneDriveFile
from src.core.data_access import DataAccess
from src.core.graph_client import MSGraphClient
from src.core.auth import MSGraphAuth
import msal

@pytest.fixture
def msal_app():
    client_id = os.environ["CLIENT_ID"]
    client_secret = os.environ["CLIENT_SECRET"]
    tenant_id = os.environ["TENANT_ID"]
    return MSGraphAuth(
        client_id=client_id,
        client_secret=client_secret,
        tenant_id=tenant_id
    )

@pytest.fixture
async def graph_client(msal_app):
    return MSGraphClient(auth=msal_app)

@pytest.fixture
def data_access(msal_app):
    return DataAccess(msal_app)

@pytest.mark.asyncio
async def test_get_recent_data_with_real_api(data_access):
    """Test get_recent_data with real Microsoft Graph API"""
    entries = await data_access.get_recent_data(limit=5)
    
    # Basic validation
    assert len(entries) > 0
    assert all(entry.metadata is not None for entry in entries)
    
    # Check for URLs in metadata
    for entry in entries:
        assert "url" in entry.metadata
        if entry.source == DataSource.OUTLOOK_EMAIL:
            assert entry.metadata["url"].startswith("https://outlook.office.com/mail/id/")
        elif entry.source == DataSource.ONEDRIVE_FILE:
            assert entry.metadata["url"].startswith("https://")

@pytest.mark.asyncio
async def test_search_data_with_real_api(data_access):
    """Test search_data with real Microsoft Graph API"""
    # Search for recent items
    query = SearchQuery(
        query="test",
        limit=5
    )
    response = await data_access.search_data(query)
    
    # Basic validation
    assert len(response.results) > 0
    assert all(entry.metadata is not None for entry in response.results)
    
    # Check for URLs in metadata
    for entry in response.results:
        assert "url" in entry.metadata
        if entry.source == DataSource.OUTLOOK_EMAIL:
            assert entry.metadata["url"].startswith("https://outlook.office.com/mail/id/")
        elif entry.source == DataSource.ONEDRIVE_FILE:
            assert entry.metadata["url"].startswith("https://")

@pytest.mark.asyncio
async def test_answer_question_with_real_api(data_access):
    """Test answer_question with real Microsoft Graph API"""
    # First get some recent entries
    entries = await data_access.get_recent_data(limit=2)
    if not entries:
        pytest.skip("No recent entries found to test with")
    
    # Use the IDs of the recent entries
    context_ids = [entry.id for entry in entries]
    
    # Test with a simple question
    answer = await data_access.answer_question(
        "What is this about?",
        context_ids
    )
    
    # Basic validation
    assert isinstance(answer, str)
    assert len(answer) > 0
    
    # Check that URLs are included in the answer
    for entry in entries:
        assert entry.metadata["url"] in answer 

def entry_to_context(entry, content_chars=200):
    # Build lines from metadata
    meta_lines = [f"{k}: {v}" for k, v in entry.metadata.items()]
    # Prefer summary if available, else use the start of content
    if "summary" in entry.metadata and entry.metadata["summary"]:
        meta_lines.append(f"Summary: {entry.metadata['summary']}")
    elif entry.content:
        preview = entry.content[:content_chars]
        meta_lines.append(f"Content Preview: {preview}")
    return "\n".join(meta_lines)

# When preparing context for the LLM:
context = "\n\n".join(entry_to_context(entry) for entry in entries) 