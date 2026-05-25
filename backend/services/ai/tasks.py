from __future__ import annotations

from celery import Celery
from services.shared.config import settings

celery_app = Celery(
    "idp_tasks",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

@celery_app.task
def generate_chat_title(session_id: str, first_query: str):
    """Generate title for chat session based on first query."""
    from services.ai.pipeline.llm_generation import LlmGenerator
    import asyncio

    llm = LlmGenerator()
    prompt = f"Hãy tóm tắt câu hỏi sau thành một tiêu đề hội thoại ngắn gọn (dưới 10 từ) bằng tiếng Việt: {first_query}"

    # Simple non-async wrapper for demo
    async def _run():
        response = ""
        async for chunk in llm.client.models.generate_content_stream(
            model="gemini-2.0-flash",
            contents=prompt
        ):
            response += chunk.text or ""
        return response.strip().strip('"')

    title = asyncio.run(_run())

    # Update DB
    from services.shared.database import DatabasePool
    async def _update():
        await DatabasePool.connect()
        pool = DatabasePool.get_pool()
        async with pool.acquire() as conn:
            await conn.execute("UPDATE chat.sessions SET title = $1 WHERE id = $2;", title, session_id)
        await DatabasePool.disconnect()

    asyncio.run(_update())

@celery_app.task
def suggest_follow_up(session_id: str, last_query: str):
    """Generate 3 follow-up questions."""
    pass # Implementation deferred to future refinements
