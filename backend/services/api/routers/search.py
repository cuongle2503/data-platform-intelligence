from fastapi import APIRouter, Depends, Query
from typing import List, Dict, Any

from services.ai.elasticsearch.es_search import ElasticSearcher

router = APIRouter(prefix="/api/search", tags=["search"])

@router.get("", response_model=List[Dict[str, Any]])
async def search_lexical(
    q: str = Query(..., description="Search query"),
    limit: int = Query(10, description="Max results")
):
    """Lexical search via Elasticsearch."""
    searcher = ElasticSearcher()
    try:
        results = await searcher.search_indicators(q, size=limit)
        return results
    finally:
        await searcher.close()
