from __future__ import annotations

from typing import List

from google import genai
from google.genai import types

from services.shared.config import settings
from services.shared.logging import get_logger

logger = get_logger(__name__)

class GeminiEmbedder:
    """Embed texts using Gemini Embeddings API (text-embedding-004, 768d)."""

    def __init__(self):
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is not set")
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model = "gemini-embedding-2"
        self.dimension = 768

    async def embed_texts(self, texts: List[str], task_type: str = "RETRIEVAL_DOCUMENT") -> List[List[float]]:
        """Embed multiple texts. Returns list of embedding vectors."""
        embeddings = []
        for text in texts:
            resp = self.client.models.embed_content(
                model=self.model,
                contents=text,
                config=types.EmbedContentConfig(
                    task_type=task_type
                )
            )
            embeddings.append(list(resp.embeddings[0].values))
        logger.info("Embedded texts", count=len(texts))
        return embeddings

    async def embed_query(self, text: str) -> List[float]:
        """Embed a search query."""
        resp = self.client.models.embed_content(
            model=self.model,
            contents=text,
            config=types.EmbedContentConfig(
                task_type="RETRIEVAL_QUERY"
            )
        )
        return list(resp.embeddings[0].values)
