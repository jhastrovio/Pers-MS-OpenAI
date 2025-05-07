from pydantic_settings import BaseSettings

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
    azure_openai_api_version: str
    azure_completion_deployment_id: str
    
    # Token settings
    TOKEN_EXPIRY_BUFFER: int = 300  # 5 minutes buffer for token expiry
    
    # API settings
    API_VERSION: str = "v1.0"

settings = Settings() 