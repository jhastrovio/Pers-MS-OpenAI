from pydantic_settings import BaseSettings
from typing import Optional
import json
from pathlib import Path

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
    azure_embedding_model: str
    azure_embedding_deployment_id: str
    azure_completion_model: str
    azure_deployment_id: str
    azure_openai_api_version: str
    
    # Token settings
    TOKEN_EXPIRY_BUFFER: int = 300  # 5 minutes buffer for token expiry
    
    # API settings
    API_VERSION: str = "v1.0"
    
    @classmethod
    def load_from_secrets(cls, secrets_path: str = "config/secrets.json") -> 'Settings':
        """Load settings from a secrets.json file"""
        secrets_path = Path(secrets_path)
        if not secrets_path.exists():
            raise FileNotFoundError(f"Secrets file not found at {secrets_path}")
        
        with open(secrets_path) as f:
            secrets = json.load(f)
        
        return cls(**secrets)

settings = Settings.load_from_secrets() 