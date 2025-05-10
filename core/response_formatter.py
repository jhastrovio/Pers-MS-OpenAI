from typing import List, Dict, Optional

def format_response_json(answer: str, citations: List[Dict], confidence: Optional[float] = None) -> Dict:
    """
    Returns a structured response as a dict/JSON.
    citations: list of dicts, e.g. [{"source": "file.pdf", "page": 3, "type": "drive"}]
    """
    return {
        "answer": answer,
        "citations": citations,
        "confidence": confidence
    }

def response_to_text(response: Dict) -> str:
    """
    Converts a structured response dict to a user-friendly plain text string.
    Handles different citation types (drive, email, data) with type-specific formatting.
    """
    answer = response.get("answer", "")
    citations = response.get("citations", [])
    confidence = response.get("confidence")

    citation_strs = []
    for c in citations:
        ctype = c.get("type")
        if ctype == "drive":
            # Example: report.pdf, p.2 (drive)
            s = f"{c.get('source', '?')}"
            if "page" in c:
                s += f", p.{c['page']}"
            s += " (drive)"
            citation_strs.append(s)
        elif ctype == "email":
            # Example: Email: Q2 Results (Outlook)
            subj = c.get('subject', 'No subject')
            s = f"Email: {subj} (Outlook)"
            citation_strs.append(s)
        elif ctype == "data":
            # Example: Table: monthly_sales (data)
            s = f"Table: {c.get('table', 'unknown')} (data)"
            citation_strs.append(s)
        else:
            # Fallback: print the dict as-is
            citation_strs.append(str(c))
    citation_text = ""
    if citation_strs:
        citation_text = " [" + "; ".join(citation_strs) + "]"

    conf_text = f"\nConfidence: {confidence:.2f}" if confidence is not None else ""
    return f"{answer}{citation_text}{conf_text}"

# Example usage
if __name__ == "__main__":
    resp = format_response_json(
        answer="The Q2 report is ready.",
        citations=[
            {"type": "drive", "source": "report.pdf", "page": 2},
            {"type": "email", "source": "Outlook", "subject": "Q2 Results", "message_id": "AAMkAGQ0..."},
            {"type": "data", "source": "sales_db", "table": "monthly_sales", "row_id": 123}
        ],
        confidence=0.92
    )
    print(response_to_text(resp)) 