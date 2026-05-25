from __future__ import annotations

from typing import List, Dict, Any

import asyncpg

from services.shared.database import DatabasePool
from services.ai.embeddings.embedder import GeminiEmbedder

class VectorSearcher:
    def __init__(self):
        self.embedder = GeminiEmbedder()

    async def search(self, query: str, top_k: int = 20) -> List[Dict[str, Any]]:
        """Semantic search using pgvector cosine distance."""
        query_embedding = await self.embedder.embed_query(query)
        embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

        sql = """
            SELECT
                source_id,
                source_type,
                metadata,
                1.0 - (embedding <=> $1::vector) AS similarity
            FROM embeddings.economic_embeddings
            ORDER BY embedding <=> $1::vector
            LIMIT $2;
        """

        pool = DatabasePool.get_pool()
        async with pool.acquire() as conn:
            records = await conn.fetch(sql, embedding_str, top_k)

        return [dict(r) for r in records]
