import pytest
from core import intent_classifier


def test_load_model_and_vectorizer():
    model, vectorizer = intent_classifier.load_model_and_vectorizer()
    assert model is not None
    assert vectorizer is not None


def test_classify_intent_email():
    query = "Show me my latest emails from Alice"
    intent = intent_classifier.classify_intent(query)
    assert intent in {"email", "mixed"}  # Accept mixed if classifier is not strict


def test_classify_intent_drive():
    query = "Find the Q2 report in OneDrive"
    intent = intent_classifier.classify_intent(query)
    assert intent in {"drive", "mixed"}


def test_classify_intent_data():
    query = "Summarize the monthly sales table"
    intent = intent_classifier.classify_intent(query)
    assert intent in {"data", "mixed"}


def test_classify_intent_mixed():
    query = "Search my emails and files for project updates"
    intent = intent_classifier.classify_intent(query)
    assert intent == "mixed"


def test_classify_intent_empty():
    query = ""
    intent = intent_classifier.classify_intent(query)
    assert intent in {"email", "drive", "mixed", "data"}  # Should not error 