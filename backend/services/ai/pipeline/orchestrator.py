from __future__ import annotations

import asyncio
from typing import AsyncGenerator

from services.shared.logging import get_logger
from services.ai.elasticsearch.es_search import ElasticSearcher
from services.ai.embeddings.vector_search import VectorSearcher
from services.ai.graph.traversal import GraphTraversal
from services.ai.pipeline.query_expansion import QueryExpansion, RrFFusion
from services.ai.pipeline.filter_rerank import FilterRerank, ContextAssembly
from services.ai.pipeline.llm_generation import LlmGenerator
from services.ai.pipeline.structured_retrieval import StructuredRetriever

logger = get_logger(__name__)

class GraphAugmentedRAG:
    """Orchestrates the 14-step Graph-Augmented RAG Pipeline."""

    def __init__(self):
        self.es_searcher = ElasticSearcher()
        self.vector_searcher = VectorSearcher()
        self.graph_traversal = GraphTraversal()
        self.llm = LlmGenerator()

    async def process_query_stream(self, user_query: str) -> AsyncGenerator[str, None]:
        """Execute pipeline and stream results."""
        logger.info("RAG Pipeline started", query=user_query)

        # 1. Query Expansion
        queries = QueryExpansion.expand(user_query)
        search_query = " ".join(queries)

        # 2-3. Parallel Lexical & Semantic Search
        lexical_res, semantic_res = [], []
        try:
            lexical_res = await self.es_searcher.search_indicators(search_query, size=15)
        except Exception as e:
            logger.error("Lexical search failed", error=str(e))

        try:
            semantic_res = await self.vector_searcher.search(search_query, top_k=15)
        except Exception as e:
            logger.error("Semantic search failed", error=str(e))

        # 4. RRF Fusion (Anchor Nodes)
        anchors = RrFFusion.fuse(lexical_res, semantic_res)

        if not anchors:
            yield "Không tìm thấy thông tin ngữ cảnh nào phù hợp với câu hỏi của bạn."
            return

        # 5. Graph Expansion
        try:
            graph_nodes = self.graph_traversal.expand_context(anchors, max_nodes=50)
            # Combine anchors + expanded
            all_nodes = anchors + graph_nodes
        except Exception as e:
            logger.error("Graph traversal failed, falling back to anchors only", error=str(e))
            all_nodes = anchors

        # 6-7. Filter and Rerank
        ranked_nodes = FilterRerank.filter_and_rank(all_nodes)

        # 7.5. Structured Fact Retrieval (Phase 6 Enhancement)
        import re
        fact_results = []

        # Resolve countries (multi-country support)
        countries_map = {"việt nam": "VNM", "vietnam": "VNM", "vnm": "VNM",
                         "indonesia": "IDN", "idn": "IDN",
                         "thái lan": "THA", "thailand": "THA", "tha": "THA",
                         "singapore": "SGP", "sgp": "SGP",
                         "philippines": "PHL", "phl": "PHL",
                         "malaysia": "MYS", "mys": "MYS",
                         "brunei": "BRN", "brn": "BRN",
                         "cambodia": "KHM", "campuchia": "KHM", "khm": "KHM",
                         "laos": "LAO", "lao": "LAO",
                         "myanmar": "MMR", "mmr": "MMR",
                         "timor-leste": "TLS", "tls": "TLS"}

        target_countries = []
        if "asean" in user_query.lower() or "đông nam á" in user_query.lower():
            target_countries = ["VNM", "IDN", "THA", "SGP", "PHL", "MYS", "BRN", "KHM", "LAO", "MMR", "TLS"]
        else:
            for name, code in countries_map.items():
                if name in user_query.lower():
                    if code not in target_countries:
                        target_countries.append(code)

        if not target_countries:
            target_countries = ["VNM"] # Default

        is_comparison = any(x in user_query.lower() for x in ["so sánh", "xu hướng", "tăng trưởng", "biến động", "trend", "compare"])

        for node in ranked_nodes:
            if node.get("type") == "Indicator":
                for country_code in target_countries:
                    try:
                        if is_comparison:
                            # Get all years for comparison/trends
                            rows = await StructuredRetriever.get_timeseries(country_code, node["id"])
                            for res in rows:
                                fact_results.append(f"FACT: {res['country_name']} - {res['indicator_name']} ({res['year']}): {res['value']:,} {res.get('unit', '')}")
                        else:
                            # Single point lookup
                            year_match = re.search(r'\b(20\d{2})\b', user_query)
                            target_year = int(year_match.group(1)) if year_match else None
                            res = await StructuredRetriever.get_fact_value(country_code, node["id"], target_year)
                            if res:
                                fact_results.append(f"FACT: {res['country_name']} - {res['indicator_name']} ({res['year']}): {res['value']:,} {res.get('unit', '')}")
                    except Exception as e:
                        logger.error("Fact retrieval failed", country=country_code, error=str(e))

        context = ContextAssembly.assemble(ranked_nodes)
        if fact_results:
            context += "\n\n--- REAL DATA VALUES ---\n" + "\n".join(fact_results)
        logger.info("Context assembled", num_nodes=len(ranked_nodes), context_length=len(context))

        # 9-11. LLM Generation
        async for chunk in self.llm.generate_stream(context, user_query):
            yield chunk

    async def close(self):
        await self.es_searcher.close()
        self.graph_traversal.close()

# Singleton instance
rag_pipeline = GraphAugmentedRAG()
