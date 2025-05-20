from dotenv import load_dotenv
import os
import logging
from openai import OpenAI
from typing import List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv(override=True)  # Force override any existing values

class AssistantManager:
    def __init__(self):
        # Get API key directly from environment
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            logger.error("OPENAI_API_KEY not found in environment")
            raise ValueError("OPENAI_API_KEY not found in environment")
            
        logger.info(f"Initializing AssistantManager with API key length: {len(api_key)}")
        logger.info(f"API key starts with: {api_key[:8]}...")
        
        self.client = OpenAI(api_key=api_key)
        self.assistant_id = os.environ.get("ASSISTANT_ID")
        logger.info(f"Assistant ID from env: {self.assistant_id}")
        
    async def get_or_create_assistant(
        self,
        name: str = "Knowledge-Assistant",
        model: str = "gpt-4-turbo-preview",
        tools: List[str] = ["file_search"],
        instructions: str = "Answer only from the provided company documents.",
        file_ids: Optional[List[str]] = None
    ) -> str:
        """Get existing assistant or create new one if none exists"""
        if self.assistant_id:
            try:
                # Verify the assistant exists
                await self.get_assistant()
                logger.info(f"Using existing assistant with ID: {self.assistant_id}")
                return self.assistant_id
            except Exception as e:
                logger.warning(f"Existing assistant not found: {str(e)}, creating new one")
                self.assistant_id = None
                
        # Create new assistant if none exists
        return await self.create_assistant(
            name=name,
            model=model,
            tools=tools,
            instructions=instructions,
            file_ids=file_ids
        )
        
    async def create_assistant(
        self,
        name: str = "Knowledge-Assistant",
        model: str = "gpt-4-turbo-preview",
        tools: List[str] = ["file_search"],
        instructions: str = "Answer only from the provided company documents.",
        file_ids: Optional[List[str]] = None
    ) -> str:
        """Create a new assistant and return its ID"""
        try:
            logger.info(f"Creating assistant with name: {name}, model: {model}")
            logger.info(f"Using API key starting with: {self.client.api_key[:8]}...")
            
            # Prepare assistant creation parameters
            params = {
                "name": name,
                "model": model,
                "tools": [{"type": tool} for tool in tools],
                "instructions": instructions
            }
            
            # Only add file_ids if provided and not empty
            if file_ids and len(file_ids) > 0:
                params["file_ids"] = file_ids
                
            logger.info(f"Creating assistant with params: {params}")
            assistant = self.client.beta.assistants.create(**params)
            self.assistant_id = assistant.id  # Update the instance variable
            logger.info(f"Successfully created assistant with ID: {assistant.id}")
            return assistant.id
        except Exception as e:
            logger.error(f"Failed to create assistant. Error type: {type(e).__name__}")
            logger.error(f"Error details: {str(e)}")
            raise Exception(f"Failed to create assistant: {str(e)}")

    async def get_assistant(self) -> dict:
        """Retrieve the current assistant configuration"""
        if not self.assistant_id:
            logger.error("ASSISTANT_ID not configured")
            raise Exception("ASSISTANT_ID not configured")
            
        try:
            logger.info(f"Retrieving assistant with ID: {self.assistant_id}")
            return self.client.beta.assistants.retrieve(self.assistant_id)
        except Exception as e:
            logger.error(f"Failed to retrieve assistant: {str(e)}")
            raise Exception(f"Failed to retrieve assistant: {str(e)}")

# Initialize the assistant manager
assistant_manager = AssistantManager()
