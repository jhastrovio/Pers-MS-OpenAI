from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from actions.data_actions import router as data_router
from actions.auth_actions import router as auth_router
import os
from dotenv import load_dotenv
from fastapi.security import APIKeyHeader

# Load environment variables from .env file
load_dotenv()

# API key dependency
API_KEY = os.getenv("P_Deploy_API_Key")

# API key security scheme for Swagger UI
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# API key dependency using FastAPI's security utility
async def api_key_auth(api_key: str = Depends(api_key_header)):
    if not api_key or api_key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key",
        )

app = FastAPI(
    title="Personal MS Assistant ChatGPT Actions",
    description="API endpoints for ChatGPT actions integration",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(data_router, dependencies=[Depends(api_key_auth)])

@app.get("/")
async def root():
    return {"message": "Personal MS Assistant ChatGPT Actions API is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 