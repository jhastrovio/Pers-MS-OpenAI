import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()
print("DEBUG: REDIRECT_URI =", os.environ.get("REDIRECT_URI"))

class Settings(BaseSettings):
    # Azure AD App Registration settings
    tenant_id: str
    client_id: str
    client_secret: str
    user_email: str
    
    # Azure OpenAI settings
    openai_api_key: str
    azure_openai_endpoint: str
    azure_openai_key: str
    azure_embedding_deployment_id: str
    azure_completion_deployment_id: str
    azure_openai_embed_endpoint: str
    azure_openai_embed_api_key: str
    
    # Token settings
    TOKEN_EXPIRY_BUFFER: int = 300  # 5 minutes buffer for token expiry
    
    # API settings
    API_VERSION: str = "v1.0"

    # Use environment variable for redirect_uri, fallback to localhost for local dev
    redirect_uri: str  # Must be set in environment

    # Separate API versions for completions and embeddings
    azure_completion_api_version: str = os.environ.get("AZURE_COMPLETION_API_VERSION", "2023-05-15")
    azure_embedding_api_version: str = os.environ.get("AZURE_EMBEDDING_API_VERSION", "2023-05-15")

settings = Settings() 