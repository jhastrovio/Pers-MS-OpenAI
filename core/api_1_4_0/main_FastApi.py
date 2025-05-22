from dotenv import load_dotenv
import os, uuid, asyncio, openai
import logging
from core.utils.logging import configure_logging
from fastapi import FastAPI, Header, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional, Union
from .assistant import assistant_manager

# Configure logging
configure_logging(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv(override=True)  # Force override any existing values

# Log environment variables (without exposing the full API key)
openai_api_key = os.environ.get("OPENAI_API_KEY")
if not openai_api_key:
    logger.error("OPENAI_API_KEY not found in environment")
    raise ValueError("OPENAI_API_KEY not found in environment")

logger.info(f"OpenAI API Key configured: {bool(openai_api_key)}")
logger.info(f"OpenAI API Key length: {len(openai_api_key)}")
logger.info(f"API key starts with: {openai_api_key[:8]}...")

openai.api_key = openai_api_key
openai.api_type = "openai"  # Set API type to openai
ASSISTANT_ID   = os.environ.get("ASSISTANT_ID")      # from step 1
API_KEY_PROXY  = os.environ.get("PROXY_TOKEN")       # shared secret for the GPT Action

logger.info(f"Assistant ID configured: {bool(ASSISTANT_ID)}")
logger.info(f"Proxy Token configured: {bool(API_KEY_PROXY)}")

# CORS configuration
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
ALLOWED_METHODS = ["GET", "POST"]
ALLOWED_HEADERS = ["*"]

threads: Dict[str, str] = {}   # {conversation_id: thread_id}

class Ask(BaseModel):
    conversation_id: Optional[str] = Field(None, description="Unique identifier for the conversation. If not provided, a new conversation will be created.")
    query: str = Field(..., description="The user's question or message to the assistant")
    
    class Config:
        schema_extra = {
            "example": {
                "conversation_id": None,
                "query": "Hello, can you help me with a question?"
            }
        }

class APIError(Exception):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(self.message)

class HealthResponse(BaseModel):
    status: str = Field(..., description="Health status of the API")
    version: str = Field(..., description="API version")
    openai_configured: bool = Field(..., description="Whether OpenAI API is configured")
    assistant_configured: bool = Field(..., description="Whether the assistant is configured")

class AskResponse(BaseModel):
    conversation_id: str = Field(..., description="Unique identifier for the conversation")
    answer: str = Field(..., description="The assistant's response")

class AssistantCreateResponse(BaseModel):
    assistant_id: str = Field(..., description="The ID of the created or retrieved assistant")

class AssistantInfoResponse(BaseModel):
    id: str = Field(..., description="The assistant's ID")
    name: str = Field(..., description="The assistant's name")
    model: str = Field(..., description="The model used by the assistant")
    tools: List[str] = Field(..., description="List of tools the assistant can use")
    instructions: Optional[str] = Field(None, description="Instructions for the assistant")

app = FastAPI(
    title="Assistant API",
    description="API for interacting with OpenAI Assistant",
    version="1.4.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    swagger_ui_parameters={"defaultModelsExpandDepth": -1}
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=ALLOWED_METHODS,
    allow_headers=ALLOWED_HEADERS,
)

class AssistantConfig(BaseModel):
    name: str = Field("Knowledge-Assistant", description="The name of the assistant")
    model: str = Field("gpt-4-turbo-preview", description="The OpenAI model to use")
    tools: List[str] = Field(["file_search"], description="List of tools the assistant can use")
    instructions: str = Field("Answer only from the provided company documents.", description="Instructions for the assistant")
    file_ids: Optional[List[str]] = Field(None, description="List of file IDs to attach to the assistant")
    
    class Config:
        schema_extra = {
            "example": {
                "name": "Knowledge-Assistant",
                "model": "gpt-4-turbo-preview",
                "tools": ["file_search"],
                "instructions": "Answer only from the provided company documents.",
                "file_ids": None
            }
        }

@app.get("/")
def root():
    """Root endpoint to check if the API is running"""
    return {"status": "OK"}

@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint to verify API status
    
    Returns:
        Dict with status information about the API
    """
    return {
        "status": "healthy",
        "version": "1.4.0",
        "openai_configured": bool(openai.api_key),
        "assistant_configured": bool(ASSISTANT_ID)
    }

@app.post("/ask", response_model=AskResponse, tags=["Assistant"], responses={
    401: {"description": "Invalid API key"},
    500: {"description": "Internal server error"}
})
async def ask(body: Ask, x_api_key: str = Header(default="")) -> Dict[str, Any]:
    """
    Send a question to the assistant and get a response
    
    Args:
        body: The question and optional conversation ID
        x_api_key: API key for authentication
        
    Returns:
        Dict with conversation ID and assistant's answer
    """
    try:
        if x_api_key != API_KEY_PROXY:
            raise APIError(401, "Invalid API key")

        conv_id = body.conversation_id or str(uuid.uuid4())
        thread_id = threads.get(conv_id)
        loop = asyncio.get_event_loop()

        if not thread_id:
            thread = await loop.run_in_executor(None, openai.beta.threads.create)
            thread_id = thread.id
            threads[conv_id] = thread_id

        # Add user message
        await loop.run_in_executor(
            None,
            lambda: openai.beta.threads.messages.create(
                thread_id, role="user", content=body.query
            )
        )
        # Start assistant run
        run = await loop.run_in_executor(
            None,
            lambda: openai.beta.threads.runs.create(
                thread_id=thread_id, assistant_id=ASSISTANT_ID
            )
        )
        run_id = run.id
        # Poll for completion
        status = run.status
        while status not in ("completed", "failed", "cancelled", "expired"):
            await asyncio.sleep(1)
            run = await loop.run_in_executor(
                None,
                lambda: openai.beta.threads.runs.retrieve(
                    thread_id=thread_id, run_id=run_id
                )
            )
            status = run.status
        if status != "completed":
            raise APIError(500, f"Run failed: {status}")
        # Get answer
        msgs = await loop.run_in_executor(
            None,
            lambda: openai.beta.threads.messages.list(thread_id, limit=1)
        )
        answer = msgs.data[0].content[0].text.value
        return {"conversation_id": conv_id, "answer": answer}
    except APIError as e:
        raise HTTPException(e.status_code, e.message)
    except Exception as e:
        raise HTTPException(500, f"Internal server error: {str(e)}")

@app.post("/assistant/create", response_model=AssistantCreateResponse, tags=["Assistant"], responses={
    401: {"description": "Invalid API key"},
    500: {"description": "Internal server error"}
})
async def create_assistant(
    config: AssistantConfig,
    x_api_key: str = Header(default="")
) -> Dict[str, Any]:
    """
    Get existing assistant or create new one if none exists
    
    Args:
        config: Configuration for the assistant
        x_api_key: API key for authentication
        
    Returns:
        Dict with the assistant ID
    """
    try:
        if x_api_key != API_KEY_PROXY:
            raise APIError(401, "Invalid API key")
            
        logger.info("Getting or creating assistant with config: %s", config.dict())
        assistant_id = await assistant_manager.get_or_create_assistant(
            name=config.name,
            model=config.model,
            tools=config.tools,
            instructions=config.instructions,
            file_ids=config.file_ids
        )
        return {"assistant_id": assistant_id}
    except Exception as e:
        logger.error("Error with assistant: %s", str(e))
        raise HTTPException(500, str(e))

@app.get("/assistant/info", response_model=AssistantInfoResponse, tags=["Assistant"], responses={
    401: {"description": "Invalid API key"},
    500: {"description": "Internal server error"}
})
async def get_assistant_info(x_api_key: str = Header(default="")) -> Dict[str, Any]:
    """
    Get information about the current assistant
    
    Args:
        x_api_key: API key for authentication
        
    Returns:
        Dict with assistant information including ID, name, model, etc.
    """
    try:
        if x_api_key != API_KEY_PROXY:
            raise APIError(401, "Invalid API key")
            
        assistant = await assistant_manager.get_assistant()
        return {
            "id": assistant.id,
            "name": assistant.name,
            "model": assistant.model,
            "tools": [tool.type for tool in assistant.tools],
            "instructions": assistant.instructions
        }
    except Exception as e:
        raise HTTPException(500, str(e))
