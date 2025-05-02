from typing import Optional, Dict
from datetime import datetime, timedelta
import msal
from pathlib import Path
import json
from .config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AuthService:
    def __init__(self):
        self._cache = {}
        self._token_file = Path("config/token_cache.json")
        self._app = msal.ConfidentialClientApplication(
            client_id=settings.client_id,
            client_credential=settings.client_secret,
            authority=f"https://login.microsoftonline.com/{settings.tenant_id}",
            token_cache=self._load_token_cache()
        )

    def _load_token_cache(self) -> msal.SerializableTokenCache:
        """Load token cache from file"""
        cache = msal.SerializableTokenCache()
        if self._token_file.exists():
            cache.deserialize(self._token_file.read_text())
        return cache

    def _save_token_cache(self):
        """Save token cache to file"""
        if self._app.token_cache.has_state_changed:
            self._token_file.write_text(self._app.token_cache.serialize())

    async def get_access_token(self) -> str:
        """Get a valid access token, either from cache or by acquiring a new one"""
        # Try to get token from cache first
        accounts = self._app.get_accounts()
        if accounts:
            result = self._app.acquire_token_silent(
                scopes=["https://graph.microsoft.com/.default"],
                account=accounts[0]
            )
            if result:
                return result["access_token"]

        # If no token in cache or expired, get new token
        result = self._app.acquire_token_for_client(
            scopes=["https://graph.microsoft.com/.default"]
        )
        
        if "error" in result:
            raise Exception(f"Token acquisition failed: {result.get('error_description', result['error'])}")
        
        self._save_token_cache()
        return result["access_token"]

    async def get_token_for_user(self, user_email: str) -> str:
        """Get a token for a specific user"""
        result = self._app.acquire_token_for_client(
            scopes=[
                "https://graph.microsoft.com/Mail.Read",
                "https://graph.microsoft.com/Files.Read.All",
                f"https://graph.microsoft.com/User.Read.All"
            ]
        )
        
        if "error" in result:
            raise Exception(f"Token acquisition failed: {result.get('error_description', result['error'])}")
        
        self._save_token_cache()
        return result["access_token"]

    def is_token_expired(self, token: Dict) -> bool:
        """Check if a token is expired or about to expire"""
        if "expires_in" not in token:
            return True
        
        expiry_time = datetime.fromtimestamp(token.get("expires_at", 0))
        buffer_time = timedelta(seconds=300)  # 5 minutes buffer
        return datetime.utcnow() + buffer_time >= expiry_time

class MSGraphAuth:
    def __init__(self, client_id: str, client_secret: str, tenant_id: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.tenant_id = tenant_id
        self.authority = f"https://login.microsoftonline.com/{tenant_id}"
        self._token_cache = {}
        
    def _create_msal_app(self):
        return msal.ConfidentialClientApplication(
            client_id=self.client_id,
            authority=self.authority,
            client_credential=self.client_secret
        )

    def get_token(self, scopes: list[str]) -> str:
        """Get an access token for the specified scopes, using cache if available."""
        scope_key = ' '.join(sorted(scopes))
        
        # Check cache first
        if scope_key in self._token_cache:
            token_info = self._token_cache[scope_key]
            if datetime.now() < token_info['expires_at']:
                logger.debug("Using cached token")
                return token_info['token']
        
        # Get new token
        try:
            app = self._create_msal_app()
            result = app.acquire_token_for_client(scopes=scopes)
            
            if 'access_token' not in result:
                error_desc = result.get('error_description', 'Unknown error')
                raise Exception(f"Failed to acquire token: {error_desc}")
            
            # Cache the token with expiration
            self._token_cache[scope_key] = {
                'token': result['access_token'],
                'expires_at': datetime.now() + timedelta(seconds=result['expires_in'] - 300)  # 5 min buffer
            }
            
            logger.info("Successfully acquired new token")
            return result['access_token']
            
        except Exception as e:
            logger.error(f"Error acquiring token: {str(e)}")
            raise

    def get_graph_token(self) -> str:
        """Convenience method to get token with default Graph API scope.
        Note: When using client credentials flow, we must use .default scope.
        The actual permissions are configured in the Azure AD app registration."""
        return self.get_token(["https://graph.microsoft.com/.default"])

auth_service = AuthService() 