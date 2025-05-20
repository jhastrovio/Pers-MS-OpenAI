from dotenv import load_dotenv
import os
import openai

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
print(f"Loaded API key of length: {len(api_key) if api_key else 0}")
print(f"API key starts with: {api_key[:8]}...")

openai.api_key = api_key

try:
    # Try a simple API call
    response = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": "Hello"}]
    )
    print("API call successful!")
    print(f"Response: {response.choices[0].message.content}")
except Exception as e:
    print(f"OpenAI API call failed: {type(e).__name__}: {e}") 