import asyncio
from services.shared.database import DatabasePool

async def main():
    await DatabasePool.connect()
    pool = DatabasePool.get_pool()
    async with pool.acquire() as conn:
        sessions = await conn.fetch("SELECT id, title, created_at FROM chat.sessions ORDER BY created_at DESC LIMIT 5;")
        print("SESSIONS:")
        for s in sessions:
            print(dict(s))
            
        messages = await conn.fetch("SELECT session_id, role, LEFT(content, 50) as content FROM chat.messages ORDER BY created_at DESC LIMIT 5;")
        print("\nMESSAGES:")
        for m in messages:
            print(dict(m))
            
        count = await conn.fetchval("SELECT COUNT(*) FROM embeddings.economic_embeddings WHERE source_type = 'document';")
        print(f"\nDocument embeddings count: {count}")
    await DatabasePool.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
