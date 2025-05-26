"""
OpenAI Integration Module

This module handles all interactions with OpenAI services:
- Vector store operations
- Attribute filtering
- Response streaming
"""

from typing import Dict, Any, AsyncGenerator, List
from openai import AsyncOpenAI

from core.utils.config import config


class OpenAIClient:
    """Client for interacting with OpenAI services."""

    def __init__(self, api_key: str | None = None, vector_store_id: str | None = None):
        """Initialize the OpenAI client with API key and settings."""
        openai_cfg = config.get("openai", {})
        self.api_key = api_key or openai_cfg.get("api_key")
        self.vector_store_id = vector_store_id or openai_cfg.get("vector_store_id")

        # Lazily create the underlying OpenAI client
        self.client = AsyncOpenAI(api_key=self.api_key)

    async def query_vector_store(
        self, prompt: str, filters: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Query the vector store with a prompt and optional filters.

        Args:
            prompt: The query prompt
            filters: Optional attribute filters

        Returns:
            Query response with results
        """
        if not self.vector_store_id:
            raise ValueError("Vector store ID is not configured")

        search_kwargs: Dict[str, Any] = {}
        if filters:
            search_kwargs["filters"] = filters

        paginator = self.client.vector_stores.search(
            self.vector_store_id,
            query=prompt,
            **search_kwargs,
        )

        results: List[Dict[str, Any]] = []
        async for item in paginator:
            results.append(item)

        return {"data": results}

    async def stream_response(
        self, response: Dict[str, Any]
    ) -> AsyncGenerator[str, None]:
        """Stream a response from OpenAI.

        Args:
            response: The response to stream

        Yields:
            Chunks of the response
        """
        async for chunk in response:
            try:
                delta = chunk["choices"][0]["delta"]
                content = delta.get("content")
            except (KeyError, IndexError, TypeError):
                content = None
            if content:
                yield content

    def apply_filters(
        self, query: Dict[str, Any], filters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply attribute filters to a query.

        Args:
            query: The base query
            filters: Filters to apply

        Returns:
            Modified query with filters
        """
        if not filters:
            return query

        merged = query.copy()
        merged_filter = merged.get("filter", {})
        merged_filter.update(filters)
        merged["filter"] = merged_filter
        return merged
