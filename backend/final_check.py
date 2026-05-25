import asyncio
from services.shared.database import DatabasePool
from elasticsearch import AsyncElasticsearch
from services.shared.config import settings

async def main():
    print("--- POSTGRES (pgvector) ---")
    await DatabasePool.connect()
    pool = DatabasePool.get_pool()
    async with pool.acquire() as conn:
        ind_count = await conn.fetchval("SELECT COUNT(*) FROM embeddings.economic_embeddings WHERE source_type = 'indicator';")
        doc_count = await conn.fetchval("SELECT COUNT(*) FROM embeddings.economic_embeddings WHERE source_type = 'document';")
        print(f"Indicators embedded: {ind_count}")
        print(f"Document chunks embedded: {doc_count}")
    await DatabasePool.disconnect()

    print("\n--- ELASTICSEARCH ---")
    es = AsyncElasticsearch(settings.es_host)
    for index in ["indicators", "documents"]:
        res = await es.count(index=index)
        print(f"Index {index}: {res['count']} docs")
    await es.close()

if __name__ == "__main__":
    asyncio.run(main())
