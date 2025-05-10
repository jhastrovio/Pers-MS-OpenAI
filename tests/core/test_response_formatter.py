import pytest
from core import response_formatter


def test_format_response_json_basic():
    answer = "Test answer."
    citations = [
        {"type": "drive", "source": "file.pdf", "page": 1},
        {"type": "email", "source": "Outlook", "subject": "Test Subject"},
        {"type": "data", "source": "db", "table": "table1"}
    ]
    confidence = 0.85
    result = response_formatter.format_response_json(answer, citations, confidence)
    assert result["answer"] == answer
    assert result["citations"] == citations
    assert result["confidence"] == confidence


def test_response_to_text_all_types():
    response = {
        "answer": "Summary here.",
        "citations": [
            {"type": "drive", "source": "doc.pdf", "page": 2},
            {"type": "email", "subject": "Hello World"},
            {"type": "data", "table": "sales"}
        ],
        "confidence": 0.99
    }
    text = response_formatter.response_to_text(response)
    assert "Summary here." in text
    assert "doc.pdf, p.2 (drive)" in text
    assert "Email: Hello World (Outlook)" in text
    assert "Table: sales (data)" in text
    assert "Confidence: 0.99" in text


def test_response_to_text_empty_citations():
    response = {"answer": "No sources.", "citations": [], "confidence": None}
    text = response_formatter.response_to_text(response)
    assert text.startswith("No sources.")
    assert "Confidence" not in text


def test_response_to_text_missing_fields():
    response = {"answer": "Partial.", "citations": [{"type": "drive"}], "confidence": 0.5}
    text = response_formatter.response_to_text(response)
    assert "Partial." in text
    assert "? (drive)" in text  # source missing, should show '?'
    assert "Confidence: 0.50" in text 