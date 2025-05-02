from fastapi import APIRouter, HTTPException, Request, Response
from typing import Optional
from ..core.auth import auth_service
from ..core.config import settings

router = APIRouter(prefix="/auth", tags=["authentication"])

@router.get("/login")
async def login(request: Request):
    """Start the OAuth2 login flow"""
    try:
        # Generate a state parameter for security
        state = request.query_params.get("state", "")
        auth_url = auth_service.get_auth_url(state)
        return {"auth_url": auth_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/callback")
async def callback(code: str, state: Optional[str] = None):
    """Handle the OAuth2 callback"""
    try:
        # Exchange the authorization code for tokens
        token_data = await auth_service.get_token_from_code(code)
        
        # Return the tokens to the client
        return {
            "access_token": token_data["access_token"],
            "refresh_token": token_data.get("refresh_token"),
            "expires_in": token_data.get("expires_in"),
            "token_type": token_data.get("token_type")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/refresh")
async def refresh(refresh_token: str):
    """Refresh an expired access token"""
    try:
        token_data = await auth_service.refresh_token(refresh_token)
        return {
            "access_token": token_data["access_token"],
            "refresh_token": token_data.get("refresh_token"),
            "expires_in": token_data.get("expires_in"),
            "token_type": token_data.get("token_type")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 