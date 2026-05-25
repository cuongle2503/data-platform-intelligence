from __future__ import annotations

import asyncio
from elasticsearch import AsyncElasticsearch
from elasticsearch.helpers import async_bulk
import asyncpg

from services.shared.config import settings
from services.shared.logging import get_logger
from services.shared.database import DatabasePool
from services.ai.elasticsearch.es_mappings import INDICATORS_MAPPING, DOCUMENTS_MAPPING, CHUNKS_MAPPING

logger = get_logger(__name__)

class ElasticIndexer:
    def __init__(self):
        self.es = AsyncElasticsearch(settings.es_host)

    async def close(self):
        await self.es.close()

    async def init_indices(self):
        """Create indices if they do not exist."""
        indices = [
            ("indicators", INDICATORS_MAPPING),
            ("documents", DOCUMENTS_MAPPING),
            ("document_chunks", CHUNKS_MAPPING)
        ]

        for name, mapping in indices:
            exists = await self.es.indices.exists(index=name)
            if not exists:
                logger.info(f"Creating index: {name}")
                await self.es.indices.create(index=name, body=mapping)
            else:
                logger.info(f"Index {name} already exists")

    async def index_indicators(self, pool: asyncpg.Pool):
        """Index economic indicators from PostgreSQL Gold layer."""
        query = """
            SELECT indicator_code, indicator_name, category, description
            FROM gold.dim_indicators
        """
        async with pool.acquire() as conn:
            records = await conn.fetch(query)

        actions = []
        for r in records:
            doc = dict(r)
            actions.append({
                "_index": "indicators",
                "_id": doc["indicator_code"],
                "_source": doc
            })

        if actions:
            await async_bulk(self.es, actions)
            logger.info(f"Indexed {len(actions)} indicators")

    async def index_documents(self):
        """Index document metadata from local Parquet."""
        import pandas as pd
        from pathlib import Path
        path = Path("/home/pc/my-projects/data-platform-intelligent/backend/tmp/world_bank_docs/metadata/documents.parquet")
        if not path.exists():
            logger.warning("Documents parquet not found, skipping ES indexing")
            return

        df = pd.read_parquet(path)
        records = df.to_dict("records")

        actions = []
        for r in records:
            actions.append({
                "_index": "documents",
                "_id": r["doc_id"],
                "_source": {
                    "doc_id": r["doc_id"],
                    "title": r["title"],
                    "doc_type": r.get("doc_type") or "",
                    "abstract": r.get("abstract") or "",
                    "topics": r.get("topics") or "",
                    "countries": r.get("countries") or ""
                }
            })

        if actions:
            await async_bulk(self.es, actions)
            logger.info(f"Indexed {len(actions)} documents")

    async def run_full_index(self):
        """Run full indexing process."""
        await DatabasePool.connect()
        pool = DatabasePool.get_pool()

        try:
            await self.init_indices()
            await self.index_indicators(pool)
            await self.index_documents()
        finally:
            await DatabasePool.disconnect()
            await self.close()

if __name__ == "__main__":
    asyncio.run(ElasticIndexer().run_full_index())
