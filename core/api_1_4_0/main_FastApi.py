from dotenv import load_dotenv
import os, uuid, asyncio, openai
import logging
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from .assistant import assistant_manager

# Configure logging
logging.basicConfig(level=logging.INFO)
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
    conversation_id: str | None = None
    query:           str

class APIError(Exception):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(self.message)

app = FastAPI(
    title="Assistant API",
    description="API for interacting with OpenAI Assistant",
    version="1.4.0"
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
    name: str = "Knowledge-Assistant"
    model: str = "gpt-4-turbo-preview"
    tools: List[str] = ["file_search"]
    instructions: str = "Answer only from the provided company documents."
    file_ids: Optional[List[str]] = None

@app.get("/")
def root():
    return {"status": "OK"}

@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint to verify API status"""
    return {
        "status": "healthy",
        "version": "1.4.0",
        "openai_configured": bool(openai.api_key),
        "assistant_configured": bool(ASSISTANT_ID)
    }

@app.post("/ask")
async def ask(body: Ask, x_api_key: str = Header(default="")):
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

@app.post("/assistant/create")
async def create_assistant(
    config: AssistantConfig,
    x_api_key: str = Header(default="")
) -> Dict[str, Any]:
    """Get existing assistant or create new one if none exists"""
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

@app.get("/assistant/info")
async def get_assistant_info(x_api_key: str = Header(default="")) -> Dict[str, Any]:
    """Get information about the current assistant"""
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
