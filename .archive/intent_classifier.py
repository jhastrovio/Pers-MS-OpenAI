from openai import OpenAI

# New: OpenAI-based intent classifier using Responses SDK
client = OpenAI()

def classify_intent_openai(query: str) -> str:
    """
    Classify the intent of a user query as 'email', 'drive', 'mixed', or 'data' using OpenAI Responses SDK.
    """
    prompt = (
        "Classify the following user query into one of these categories: "
        "email, drive, mixed, or data.\n\n"
        f"Query: {query}\n\n"
        "Category:"
    )
    response = client.responses.create(
        model="gpt-4o",  # or your preferred model
        input=prompt
    )
    # Post-process to ensure only valid categories are returned
    intent = response.output_text.strip().lower()
    valid_intents = {"email", "drive", "mixed", "data"}
    return intent if intent in valid_intents else "mixed"

# Example usage (for manual testing)
if __name__ == "__main__":
    test_query = "Show me my latest emails from Alice"
    print(f"Query: {test_query}")
    print(f"Predicted intent: {classify_intent_openai(test_query)}") 