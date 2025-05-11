import os
from dotenv import load_dotenv
load_dotenv()  # Ensure .env variables (including OPENAI_API_KEY) are loaded for tests

import pytest
from core.intent_classifier import classify_intent_openai

# These tests require a valid OpenAI API key and will consume tokens.

@pytest.mark.parametrize("query,expected", [
    ("Show me my latest emails from Alice", {"email", "mixed"}),
    ("Find the Q2 report in OneDrive", {"drive", "mixed"}),
    ("Summarize the monthly sales table", {"data", "mixed"}),
    ("Search my emails and files for project updates", {"mixed"}),
    ("", {"email", "drive", "mixed", "data"}),  # Should not error
])
def test_classify_intent_openai(query, expected):
    intent = classify_intent_openai(query)
    assert intent in expected

def test_classify_intent_email():
    query = "Show me my latest emails from Alice"
    intent = classify_intent_openai(query)
    assert intent in {"email", "mixed"}  # Accept mixed if classifier is not strict


def test_classify_intent_drive():
    query = "Find the Q2 report in OneDrive"
    intent = classify_intent_openai(query)
    assert intent in {"drive", "mixed"}


def test_classify_intent_data():
    query = "Summarize the monthly sales table"
    intent = classify_intent_openai(query)
    assert intent in {"data", "mixed"}


def test_classify_intent_mixed():
    query = "Search my emails and files for project updates"
    intent = classify_intent_openai(query)
    assert intent == "mixed"


def test_classify_intent_empty():
    query = ""
    intent = classify_intent_openai(query)
    assert intent in {"email", "drive", "mixed", "data"}  # Should not error

@pytest.mark.llm
def test_real_llm_intent_classification(monkeypatch):
    import openai
    test_key = os.environ.get("OPENAI_TESTING_KEY")
    if not test_key:
        pytest.skip("OPENAI_TESTING_KEY not set")
    monkeypatch.setenv("OPENAI_API_KEY", test_key)
    from openai import OpenAI
    client = OpenAI()
    prompt = (
        "Classify the following user query into one of these categories: "
        "email, drive, mixed, or data.\n\n"
        "Query: Show me my latest emails from Alice\n\n"
        "Category:"
    )
    response = client.responses.create(
        model="gpt-4o-mini",  # Use a small, cheap model
        input=prompt
    )
    intent = response.output_text.strip().lower()
    # Remove 'category:' prefix if present
    if intent.startswith("category:"):
        intent = intent.replace("category:", "").strip()
    assert intent in {"email", "mixed"} 