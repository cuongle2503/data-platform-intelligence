"""World Bank Documents Search (WDS) API client."""

from __future__ import annotations

import time

import requests

from idp.core.logging import get_logger
from idp.core.models import Document

logger = get_logger(__name__)

WDS_BASE = "https://search.worldbank.org/api/v2/wds"

QUERIES = [
    {"countrycode_exact": "VN"},
    {"countrycode_exact": "VN", "docty": "working-paper"},
    {"q": "Vietnam economic outlook"},
    {"q": "East Asia Pacific economic update"},
    {"q": "ASEAN trade development"},
]

MAX_RESULTS = 500
MAX_PAGES_PER_QUERY = 5


class WDSClient:
    """Static methods for searching the World Bank Documents API."""

    @staticmethod
    def search(
        queries: list[dict] | None = None,
        max_results: int = MAX_RESULTS,
    ) -> list[Document]:
        queries = queries or QUERIES
        seen: set[str] = set()
        results: list[Document] = []

        for params in queries:
            query_new = 0
            for attempt in range(3):
                try:
                    for page in range(MAX_PAGES_PER_QUERY):
                        if len(results) >= max_results:
                            break
                        before = len(results)
                        resp = requests.get(
                            WDS_BASE,
                            params={**params, "page": page, "rows": 50},
                            timeout=30,
                        )
                        resp.raise_for_status()
                        data = resp.json()
                        docs = data.get("documents", {})
                        total = int(data.get("total", 0))

                        if not docs:
                            break

                        for doc_id, doc in docs.items():
                            if doc_id in seen:
                                continue
                            seen.add(doc_id)
                            results.append(Document(
                                doc_id=doc_id,
                                title=WDSClient._clean(doc.get("display_title", "")),
                                abstract=WDSClient._extract_abstract(doc),
                                display_date=doc.get("display_date", "") or doc.get("docdt", ""),
                                doc_type=doc.get("docty", ""),
                                pdf_url=doc.get("pdfurl", ""),
                                countries=WDSClient._join(doc, "count"),
                                topics=WDSClient._clean(doc.get("topicv3", "")),
                                language=doc.get("lang", ""),
                            ))

                        added = len(results) - before
                        query_new += added
                        if added == 0 or (page + 1) * 50 >= total:
                            break
                        time.sleep(0.3)
                    break
                except requests.RequestException:
                    if attempt < 2:
                        time.sleep(2 * (attempt + 1))
                    else:
                        logger.warning("WDS query failed after 3 attempts")
            logger.info("+%d new docs (total: %d)", query_new, len(results))

        return results[:max_results]

    @staticmethod
    def _clean(s: str) -> str:
        return " ".join(s.split())

    @staticmethod
    def _extract_abstract(doc: dict) -> str:
        abstracts = doc.get("abstracts", {})
        if isinstance(abstracts, dict):
            for key in abstracts:
                val = abstracts[key]
                if isinstance(val, str) and len(val) > 10:
                    return WDSClient._clean(val)
        return ""

    @staticmethod
    def _join(doc: dict, field: str) -> str:
        val = doc.get(field, "")
        if isinstance(val, list):
            return ";".join(val)
        return str(val) if val else ""
