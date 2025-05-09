import openai
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Debug prints to verify environment variable loading
print("DEBUG: AZURE_OPENAI_ENDPOINT =", os.environ.get("AZURE_OPENAI_ENDPOINT"))
print("DEBUG: AZURE_EMBEDDING_API_VERSION =", os.environ.get("AZURE_EMBEDDING_API_VERSION"))
print("DEBUG: AZURE_OPENAI_KEY =", os.environ.get("AZURE_OPENAI_KEY"))
print("DEBUG: AZURE_EMBEDDING_DEPLOYMENT_ID =", os.environ.get("AZURE_EMBEDDING_DEPLOYMENT_ID"))

# Get values from environment
openai.api_type = "azure"
openai.api_base = os.environ["AZURE_OPENAI_ENDPOINT"]
openai.api_version = os.environ["AZURE_EMBEDDING_API_VERSION"]
openai.api_key = os.environ["AZURE_OPENAI_KEY"]

deployment_name = os.environ["AZURE_EMBEDDING_DEPLOYMENT_ID"]

try:
    response = openai.Embedding.create(
        input=["hello world"],
        engine=deployment_name  # For Azure, use 'engine' instead of 'model'
    )
    print("Embedding response:", response)
except Exception as e:
    print("Error:", e) 