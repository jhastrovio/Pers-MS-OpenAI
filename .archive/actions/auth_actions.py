from fastapi import APIRouter, HTTPException, Request, Response
from typing import Optional
from core.auth import auth_service
from core.config import settings

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
async def callback(request: Request):
    code = request.query_params.get("code")
    state = request.query_params.get("state")
    if not code:
        return {"error": "No code provided"}
    # Use the dynamic redirect_uri from settings
    redirect_uri = settings.redirect_uri
    token_result = auth_service.get_token_from_code(code, redirect_uri)
    return token_result

@router.post("/refresh")
async def refresh(refresh_token: str):
    """Refresh an expired access token"""
    try:
        token_data = auth_service.refresh_token(refresh_token)
        return {
            "access_token": token_data["access_token"],
            "refresh_token": token_data.get("refresh_token"),
            "expires_in": token_data.get("expires_in"),
            "token_type": token_data.get("token_type")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 