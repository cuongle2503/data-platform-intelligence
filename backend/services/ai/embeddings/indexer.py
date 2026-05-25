from __future__ import annotations

import json
import asyncpg

from services.shared.database import DatabasePool
from services.shared.logging import get_logger
from services.ai.embeddings.embedder import GeminiEmbedder

logger = get_logger(__name__)

class EmbeddingIndexer:
    def __init__(self):
        self.embedder = GeminiEmbedder()

    async def init_schema(self, pool: asyncpg.Pool):
        """Create embeddings schema and table if they don't exist."""
        async with pool.acquire() as conn:
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            await conn.execute("CREATE SCHEMA IF NOT EXISTS embeddings;")
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS embeddings.economic_embeddings (
                    id SERIAL PRIMARY KEY,
                    source_type VARCHAR NOT NULL,
                    source_id VARCHAR NOT NULL,
                    text TEXT NOT NULL,
                    embedding vector(3072),
                    metadata JSONB,
                    created_at TIMESTAMP DEFAULT NOW()
                );
            """)

    async def index_indicators(self, pool: asyncpg.Pool):
        """Embed and index indicator metadata."""
        query = """
            SELECT indicator_code, indicator_name, category, description
            FROM gold.dim_indicators
        """
        async with pool.acquire() as conn:
            records = await conn.fetch(query)

        texts = []
        sources = []
        for r in records:
            text = f"{r['indicator_code']} - {r['indicator_name']} - Category: {r['category']}"
            if r['description']:
                text += f" - {r['description']}"
            texts.append(text)
            sources.append(dict(r))

        embeddings = []
        for i, text in enumerate(texts):
            emb = await self.embedder.embed_texts([text])
            embeddings.append(emb[0])

        async with pool.acquire() as conn:
            await conn.executemany(
                """INSERT INTO embeddings.economic_embeddings (source_type, source_id, text, embedding, metadata)
                   VALUES ('indicator', $1, $2, $3::vector, $4)
                   ON CONFLICT (id) DO NOTHING;""",
                [(r['indicator_code'], texts[i], "[" + ",".join(str(x) for x in embeddings[i]) + "]", json.dumps(sources[i]))
                 for i, r in enumerate(sources)]
            )
            logger.info(f"Embedded {len(sources)} indicators")

    async def index_documents(self, pool: asyncpg.Pool):
        """Embed and index document chunks."""
        import pandas as pd
        from pathlib import Path
        path = Path("/home/pc/my-projects/data-platform-intelligent/backend/tmp/world_bank_docs/chunks/chunks.parquet")
        if not path.exists():
            logger.warning("Document chunks parquet not found, skipping vector indexing")
            return

        df = pd.read_parquet(path)
        records = df.to_dict("records")

        texts = []
        sources = []
        for r in records:
            text = f"Title: {r['title']}\nContent: {r['text']}"
            texts.append(text)
            sources.append(dict(r))

        embeddings = []
        # Batch embedding requests to avoid quota limits
        batch_size = 20
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i+batch_size]
            emb_batch = await self.embedder.embed_texts(batch_texts)
            embeddings.extend(emb_batch)

        async with pool.acquire() as conn:
            # Batch inserts
            for i in range(0, len(sources), batch_size):
                batch_sources = sources[i:i+batch_size]
                batch_embs = embeddings[i:i+batch_size]
                batch_texts = texts[i:i+batch_size]

                await conn.executemany(
                    """INSERT INTO embeddings.economic_embeddings (source_type, source_id, text, embedding, metadata)
                       VALUES ('document', $1, $2, $3::vector, $4)
                       ON CONFLICT (id) DO NOTHING;""",
                    [(r['doc_id'], batch_texts[j], "[" + ",".join(str(x) for x in batch_embs[j]) + "]", json.dumps(batch_sources[j]))
                     for j, r in enumerate(batch_sources)]
                )
        logger.info(f"Embedded {len(sources)} document chunks")

    async def run_full_index(self):
        """Run the complete embedding indexing pipeline."""
        await DatabasePool.connect()
        pool = DatabasePool.get_pool()

        try:
            await self.init_schema(pool)
            await self.index_indicators(pool)
            await self.index_documents(pool)
        finally:
            await DatabasePool.disconnect()
