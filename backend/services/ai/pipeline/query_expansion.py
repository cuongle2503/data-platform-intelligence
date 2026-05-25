from __future__ import annotations

import re
from typing import List, Dict, Any

class QueryExpansion:
    """Expand user queries with synonyms and alternative terms."""

    # Simple business rules for mapping terms to canonical data terms
    MAPPING_RULES = {
        "lạm phát": ["inflation", "CPI", "consumer price index"],
        "tăng trưởng": ["GDP", "gross domestic product", "growth"],
        "thu nhập": ["GNI", "gross national income", "income"],
        "xuất khẩu": ["export", "exports", "trade"],
        "nhập khẩu": ["import", "imports", "trade"],
        "thất nghiệp": ["unemployment", "labor", "jobless"],
        "dân số": ["population", "demographics"],
        "đầu tư": ["FDI", "foreign direct investment", "investment"],
        "việt nam": ["Vietnam", "Viet Nam", "VN", "VNM"]
    }

    @classmethod
    def expand(cls, raw_query: str) -> List[str]:
        """Expand query using mapping rules."""
        phrases = [raw_query]
        q_lower = raw_query.lower()

        for term, synonyms in cls.MAPPING_RULES.items():
            if term in q_lower:
                for syn in synonyms:
                    if syn.lower() not in q_lower:
                        phrases.append(syn)

        return list(set(phrases))

class RrFFusion:
    """Reciprocal Rank Fusion for combining lexical and semantic search results."""

    @staticmethod
    def fuse(lexical_results: List[Dict[str, Any]], semantic_results: List[Dict[str, Any]], k: int = 60, top_k: int = 20) -> List[Dict[str, Any]]:
        """Combine results and sort by RRF score."""
        scores = {}
        items = {}

        for rank, res in enumerate(lexical_results):
            doc_id = res["id"]
            if doc_id not in scores:
                scores[doc_id] = 0
            scores[doc_id] += 1 / (k + rank + 1)
            if doc_id not in items:
                items[doc_id] = {"type": "Indicator", "id": doc_id, "source_lexical": True, "properties": res.get("source", {})}

        for rank, res in enumerate(semantic_results):
            doc_id = res["source_id"]
            if doc_id not in scores:
                scores[doc_id] = 0
            scores[doc_id] += 1 / (k + rank + 1)
            metadata = res.get("metadata", {})
            if isinstance(metadata, str):
                import json
                metadata = json.loads(metadata)
            if doc_id not in items:
                items[doc_id] = {"type": "Indicator" if res.get("source_type") == "indicator" else "Document",
                                 "id": doc_id, "source_semantic": True, "properties": metadata}

        sorted_items = sorted([(scores[doc_id], doc_id) for doc_id in scores.keys()], reverse=True)
        fused = []
        for _, doc_id in sorted_items[:top_k]:
            fused.append(items[doc_id])

        return fused
