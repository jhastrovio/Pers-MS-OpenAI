from openai import AsyncOpenAI
from typing import Optional
import logging
from bs4 import BeautifulSoup

# Use AsyncOpenAI for async methods
client = AsyncOpenAI()

class OpenAIService:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def extract_text_from_html(self, html: str) -> str:
        """Extract visible text from HTML using BeautifulSoup."""
        soup = BeautifulSoup(html, "html.parser")
        return soup.get_text(separator="\n", strip=True)

    async def upload_file_to_file_search(self, file_path: Optional[str] = None, metadata: Optional[dict] = None, content: Optional[str] = None) -> str:
        """Upload a file or string content to OpenAI File Search and return the file ID."""
        # OpenAI File Search expects the file to be uploaded with purpose="assistants"
        if content is not None:
            import io
            file_obj = io.BytesIO(content.encode("utf-8"))
            file_obj.name = metadata.get("filename", "email.txt") if metadata else "email.txt"
            response = await client.files.create(
                file=file_obj,
                purpose="assistants",
                metadata=metadata if metadata else None
            )
        elif file_path is not None:
            with open(file_path, "rb") as f:
                response = await client.files.create(
                    file=f,
                    purpose="assistants",
                    metadata=metadata if metadata else None
                )
        else:
            raise ValueError("Either file_path or content must be provided.")
        file_id = response.id
        self.logger.info(f"Uploaded to File Search with file_id: {file_id}")
        return file_id

openai_service = OpenAIService() 