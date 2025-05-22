import os
from msal import ConfidentialClientApplication
from core.utils.config import app_config

client_id = os.getenv("CLIENT_ID")
client_secret = os.getenv("CLIENT_SECRET")
tenant_id = os.getenv("TENANT_ID")

print(f"CLIENT_ID: {client_id}")
print(f"CLIENT_SECRET: {'*' * len(client_secret) if client_secret else None}")
print(f"TENANT_ID: {tenant_id}")

app = ConfidentialClientApplication(
    client_id=client_id,
    client_credential=client_secret,
    authority=f"https://login.microsoftonline.com/{tenant_id}"
)
result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
print("\nMSAL acquire_token_for_client result:")
print(result)

@pytest.fixture
def msal_client():
    """Create an MSAL client for testing."""
    client_id = app_config.azure.client_id
    client_secret = app_config.azure.client_secret
    tenant_id = app_config.azure.tenant_id
    
    return MSALClient(client_id, client_secret, tenant_id) 