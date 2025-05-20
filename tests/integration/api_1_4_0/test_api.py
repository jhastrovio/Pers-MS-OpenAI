import os
import pytest
import requests
import json
from typing import Dict, Any
import logging

# Configuration
API_URL = "http://localhost:8000"  # Change this if your API runs on a different port
PROXY_TOKEN = os.getenv("PROXY_TOKEN", "test-token")  # Use your actual token in production
logger = logging.getLogger(__name__)

@pytest.fixture
def api_headers():
    """Fixture to provide API headers"""
    return {
        "x-api-key": PROXY_TOKEN,
        "Content-Type": "application/json"
    }

def make_request(
    method: str,
    endpoint: str,
    data: Dict[str, Any] = None,
    headers: Dict[str, str] = None
) -> requests.Response:
    """Helper function to make API requests"""
    url = f"{API_URL}{endpoint}"
    default_headers = {
        "x-api-key": PROXY_TOKEN,
        "Content-Type": "application/json"
    }
    if headers:
        default_headers.update(headers)
    
    response = requests.request(
        method=method,
        url=url,
        json=data,
        headers=default_headers
    )
    
    print(f"\n{method} {endpoint}")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2) if response.text else 'No content'}")
    return response

def test_health(api_headers):
    """Test the health check endpoint"""
    response = make_request("GET", "/health", headers=api_headers)
    assert response.status_code == 200
    assert "status" in response.json()
    assert response.json()["status"] == "healthy"

def test_assistant_creation(api_headers):
    """Test getting existing assistant or creating a new one"""
    data = {
        "name": "Test Assistant",
        "model": "gpt-4-turbo-preview",
        "tools": ["file_search"],
        "instructions": "This is a test assistant"
    }
    response = make_request("POST", "/assistant/create", data=data, headers=api_headers)
    assert response.status_code == 200
    assert "assistant_id" in response.json()
    assert response.json()["assistant_id"] is not None

def test_assistant_info(api_headers):
    """Test getting assistant information"""
    response = make_request("GET", "/assistant/info", headers=api_headers)
    assert response.status_code == 200
    assert "id" in response.json()
    assert "name" in response.json()

def test_ask_endpoint(api_headers):
    """Test the ask endpoint"""
    data = {
        "query": "Hello, this is a test message"
    }
    response = make_request("POST", "/ask", data=data, headers=api_headers)
    assert response.status_code == 200
    assert "conversation_id" in response.json()
    assert "answer" in response.json()
    assert response.json()["conversation_id"] is not None
    assert response.json()["answer"] is not None

def test_invalid_token():
    """Test API with invalid token"""
    response = make_request(
        "GET",
        "/health",
        headers={"x-api-key": "invalid-token"}
    )
    assert response.status_code == 200  # Health is public, should return 200

@pytest.mark.integration
class TestAPIEndpoints:
    """Integration tests for API endpoints"""
    
    def test_full_conversation_flow(self, api_headers):
        """Test a complete conversation flow"""
        # Test assistant creation
        data = {
            "name": "Test Assistant",
            "model": "gpt-4-turbo-preview",
            "tools": ["file_search"],
            "instructions": "This is a test assistant"
        }
        create_response = make_request("POST", "/assistant/create", data=data, headers=api_headers)
        assert create_response.status_code == 200
        assert "assistant_id" in create_response.json()
        
        # Get assistant info
        info_response = make_request("GET", "/assistant/info", headers=api_headers)
        assert info_response.status_code == 200
        assert "id" in info_response.json()
        assert "name" in info_response.json()
        
        # Send a message
        ask_data = {
            "query": "Hello, this is a test message"
        }
        ask_response = make_request("POST", "/ask", data=ask_data, headers=api_headers)
        assert ask_response.status_code == 200
        assert "conversation_id" in ask_response.json()
        assert "answer" in ask_response.json() 