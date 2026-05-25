from __future__ import annotations

from typing import List, Dict, Any
import httpx
from services.shared.config import settings

class ElasticSearcher:
    def __init__(self):
        self.client = httpx.AsyncClient(base_url=settings.es_host)

    async def close(self):
        await self.client.aclose()

    async def search_indicators(self, query: str, size: int = 10) -> List[Dict[str, Any]]:
        """Lexical search over indicators using raw HTTP to avoid version-compatibility header issues."""
        body = {
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": ["indicator_name^3", "indicator_code^2", "description", "category"],
                    "fuzziness": "AUTO"
                }
            },
            "size": size
        }

        response = await self.client.post("/indicators/_search", json=body)
        response.raise_for_status()
        data = response.json()

        return [
            {
                "id": hit["_id"],
                "score": hit["_score"],
                "source": hit["_source"]
            }
            for hit in data["hits"]["hits"]
        ]
