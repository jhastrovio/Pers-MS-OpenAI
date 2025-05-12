from openai import AsyncOpenAI
from typing import List, Dict, Optional
import logging
import json
import re
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

    async def get_embeddings(self, texts: List[str], model: str = "text-embedding-3-small") -> List[List[float]]:
        """Get embeddings for a list of texts using OpenAI Embeddings API."""
        results = []
        for text in texts:
            response = await client.embeddings.create(
                model=model,
                input=[text]
            )
            results.append(response.data[0].embedding)
        return results

    async def classify_content(self, text: str, categories: List[str], model: str = "gpt-4o") -> str:
        """Classify text into one of the given categories using OpenAI Responses API."""
        if "<html" in text.lower():
            text = self.extract_text_from_html(text)
        prompt = (
            f"Classify the following text into one of these categories: {', '.join(categories)}\n\n"
            f"Text:\n{text}\n\nCategory:"
        )
        response = await client.responses.create(
            model=model,
            input=prompt
        )
        return response.output_text.strip()

    async def analyze_sentiment(self, text: str, model: str = "gpt-4o") -> Dict:
        """Analyze the sentiment of text using OpenAI Responses API."""
        if "<html" in text.lower():
            text = self.extract_text_from_html(text)
        prompt = (
            "Analyze the sentiment of the following text and provide:\n"
            "1. Overall sentiment (positive, negative, neutral)\n"
            "2. Confidence score (0-1)\n"
            "3. Key phrases that influenced the sentiment\n\n"
            f"Text:\n{text}\n\n"
            "Format the response as a JSON object with these keys: sentiment, confidence, key_phrases"
        )
        response = await client.responses.create(
            model=model,
            input=prompt
        )
        content = response.output_text.strip()
        # Remove code fences if present
        content = re.sub(r"^```(?:json)?|```$", "", content, flags=re.IGNORECASE | re.MULTILINE).strip()
        return json.loads(content)

    async def answer_question(self, context: str, question: str, model: str = "gpt-4o") -> str:
        """Answer a question about the given context using OpenAI Responses API."""
        if "<html" in context.lower():
            context = self.extract_text_from_html(context)
        prompt = (
            f"Context:\n{context}\n\n"
            f"Question: {question}\n\n"
            "If the context includes any URLs, include them in your answer.\nAnswer:"
        )
        response = await client.responses.create(
            model=model,
            input=prompt
        )
        return response.output_text.strip()

    async def summarize_text(self, text: str, max_length: int = 200) -> str:
        """Summarize a text using GPT"""
        # Extract text if input looks like HTML
        if "<html" in text.lower():
            text = self.extract_text_from_html(text)
        self.logger.warning(f"Summarizing text (first 500 chars): {text[:500]}")
        prompt = f"""Please provide a concise summary of the following text in {max_length} characters or less:\n\n{text}\n\nSummary:"""
        
        response = await client.responses.create(
            model="gpt-4o",
            input=prompt
        )
        
        return response.output_text.strip()

    async def extract_key_info(self, text: str) -> Dict:
        """Extract key information from text"""
        # Extract text if input looks like HTML
        if "<html" in text.lower():
            text = self.extract_text_from_html(text)
        prompt = f"""Extract the following information from the text:
- Main topic
- Key points
- Important dates
- People involved
- Action items

Text:
{text}

Format the response as a JSON object with these keys: main_topic, key_points, important_dates, people_involved, action_items"""

        response = await client.responses.create(
            model="gpt-4o",
            input=prompt
        )
        
        content = response.output_text.strip()
        # Remove code fences if present
        content = re.sub(r"^```(?:json)?|```$", "", content, flags=re.IGNORECASE | re.MULTILINE).strip()
        return json.loads(content)

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