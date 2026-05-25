from __future__ import annotations

from typing import List, Dict, Any
from neo4j import GraphDatabase

from services.shared.config import settings
from services.shared.logging import get_logger

logger = get_logger(__name__)

class GraphTraversal:
    def __init__(self):
        self.driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password)
        )

    def close(self):
        self.driver.close()

    def expand_context(self, anchor_nodes: List[Dict[str, Any]], max_nodes: int = 100) -> List[Dict[str, Any]]:
        """
        Expand graph context from anchor nodes via 2-3 hop traversal.

        Anchor nodes have the format: {"type": "Indicator", "id": "NY.GDP.MKTP.CD"} or
                                     {"type": "Country", "id": "VNM"}
        """
        with self.driver.session() as session:
            return session.execute_read(self._expand, anchor_nodes, max_nodes)

    @staticmethod
    def _expand(tx, anchor_nodes, max_nodes):
        expanded: List[Dict[str, Any]] = []
        seen = set()

        for anchor in anchor_nodes:
            node_type = anchor["type"]
            node_id = anchor["id"]

            if node_type == "Indicator":
                query = """
                    MATCH (i:Indicator {code: $id})
                    OPTIONAL MATCH (i)-[:BELONGS_TO]->(cat:IndicatorCategory)
                    OPTIONAL MATCH (c:Country)-[:HAS_INDICATOR]->(i)
                    OPTIONAL MATCH (i)-[:SOURCED_FROM]->(src:DataTable)
                    OPTIONAL MATCH (src)-[:CONTAINS]->(col:DataColumn)
                    OPTIONAL MATCH (col)-[:DERIVED_FROM*1..2]->(upstream_col:DataColumn)
                    OPTIONAL MATCH (d:Document)-[:ABOUT]->(c)
                    WHERE d.topics CONTAINS cat.name OR d.title CONTAINS i.name
                    RETURN i, cat, c, src, col, upstream_col, d
                    LIMIT 40
                """
                result = tx.run(query, id=node_id)
                for record in result:
                    for key in ["i", "cat", "c", "src", "col", "upstream_col", "d"]:
                        node = record.get(key)
                        if node and node.element_id not in seen:
                            labels = list(node.labels)
                            label = labels[0] if labels else "Unknown"
                            expanded.append({
                                "type": label,
                                "id": node.get("code") or node.get("name") or node.get("doc_id") or node.get("id"),
                                "properties": dict(node.items())
                            })
                            seen.add(node.element_id)

            elif node_type == "Country":
                query = """
                    MATCH (c:Country {code: $id})
                    OPTIONAL MATCH (c)-[:HAS_INDICATOR]->(i:Indicator)
                    OPTIONAL MATCH (i)-[:BELONGS_TO]->(cat:IndicatorCategory)
                    RETURN c, i, cat
                    LIMIT 30
                """
                result = tx.run(query, id=node_id)
                for record in result:
                    for key in ["c", "i", "cat"]:
                        node = record.get(key)
                        if node and node.element_id not in seen:
                            expanded.append({"type": list(node.labels)[0], "id": node.get("code") or node.get("name"), "properties": dict(node.items())})
                            seen.add(node.element_id)

        logger.info("Graph traversal expanded", anchor_count=len(anchor_nodes), expanded_count=len(expanded))
        return expanded[:max_nodes]
