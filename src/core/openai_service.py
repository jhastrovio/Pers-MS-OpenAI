from typing import List, Dict, Optional
import openai
from .config import settings
import logging
from bs4 import BeautifulSoup
import json
import re

class OpenAIService:
    def __init__(self):
        # Configure OpenAI client
        openai.api_type = "azure"
        openai.api_base = settings.azure_openai_endpoint
        openai.api_version = settings.azure_openai_api_version
        openai.api_key = settings.azure_openai_key
        self.logger = logging.getLogger(__name__)

    def chunk_text(self, text: str, chunk_size: int = 1000) -> List[str]:
        """Split text into chunks of up to chunk_size characters."""
        if len(text) <= chunk_size:
            return [text]
        # Warn if chunking is needed
        self.logger.warning(f"Text length {len(text)} exceeds {chunk_size}, splitting into chunks.")
        return [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]

    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings for a list of texts, chunking if needed and averaging per input."""
        import numpy as np  # Only import if needed
        results = []
        for text in texts:
            chunks = self.chunk_text(text)
            chunk_embeddings = []
            for chunk in chunks:
                response = await openai.Embedding.acreate(
                    engine=settings.azure_embedding_deployment_id,
                    input=[chunk]
                )
                chunk_embeddings.append(response['data'][0]['embedding'])
            # Average embeddings if chunked
            if len(chunk_embeddings) > 1:
                avg_embedding = np.mean(chunk_embeddings, axis=0).tolist()
            else:
                avg_embedding = chunk_embeddings[0]
            results.append(avg_embedding)
        return results

    def extract_text_from_html(self, html: str) -> str:
        """Extract visible text from HTML using BeautifulSoup."""
        soup = BeautifulSoup(html, "html.parser")
        return soup.get_text(separator="\n", strip=True)

    async def summarize_text(self, text: str, max_length: int = 200) -> str:
        """Summarize a text using GPT"""
        # Extract text if input looks like HTML
        if "<html" in text.lower():
            text = self.extract_text_from_html(text)
        self.logger.warning(f"Summarizing text (first 500 chars): {text[:500]}")
        prompt = f"""Please provide a concise summary of the following text in {max_length} characters or less:\n\n{text}\n\nSummary:"""
        
        response = await openai.ChatCompletion.acreate(
            engine=settings.azure_deployment_id,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that summarizes text concisely."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=100,
            temperature=0.3
        )
        
        return response.choices[0].message.content.strip()

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

        response = await openai.ChatCompletion.acreate(
            engine=settings.azure_deployment_id,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that extracts structured information from text."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        
        content = response.choices[0].message.content.strip()
        # Remove code fences if present
        content = re.sub(r"^```(?:json)?|```$", "", content, flags=re.IGNORECASE | re.MULTILINE).strip()
        return json.loads(content)

    async def classify_content(self, text: str, categories: List[str]) -> str:
        """Classify text into one of the given categories"""
        # Extract text if input looks like HTML
        if "<html" in text.lower():
            text = self.extract_text_from_html(text)
        prompt = f"""Classify the following text into one of these categories: {', '.join(categories)}

Text:
{text}

Category:"""

        response = await openai.ChatCompletion.acreate(
            engine=settings.azure_deployment_id,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that classifies text into categories."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        
        return response.choices[0].message.content.strip()

    async def analyze_sentiment(self, text: str) -> Dict:
        """Analyze the sentiment of text"""
        # Extract text if input looks like HTML
        if "<html" in text.lower():
            text = self.extract_text_from_html(text)
        prompt = f"""Analyze the sentiment of the following text and provide:
1. Overall sentiment (positive, negative, neutral)
2. Confidence score (0-1)
3. Key phrases that influenced the sentiment

Text:
{text}

Format the response as a JSON object with these keys: sentiment, confidence, key_phrases"""

        response = await openai.ChatCompletion.acreate(
            engine=settings.azure_deployment_id,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that analyzes text sentiment."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        
        content = response.choices[0].message.content.strip()
        # Remove code fences if present
        content = re.sub(r"^```(?:json)?|```$", "", content, flags=re.IGNORECASE | re.MULTILINE).strip()
        return json.loads(content)

    async def answer_question(self, context: str, question: str) -> str:
        """Answer a question about the given context"""
        # Extract text if input looks like HTML
        if "<html" in context.lower():
            context = self.extract_text_from_html(context)
        prompt = f"""Context:
{context}

Question: {question}

Answer:"""

        response = await openai.ChatCompletion.acreate(
            engine=settings.azure_deployment_id,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that answers questions based on the given context."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        
        return response.choices[0].message.content.strip()

openai_service = OpenAIService() 