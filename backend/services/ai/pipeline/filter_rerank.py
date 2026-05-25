from __future__ import annotations

from typing import List, Dict, Any

class FilterRerank:
    """Filter and rerank graph nodes."""

    @staticmethod
    def filter_and_rank(nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply business rules to nodes."""
        valid_nodes = []
        for node in nodes:
            # Skip deprecated
            props = node.get("properties", {})
            if props.get("is_deprecated") is True:
                continue

            score = 1.0
            node_type = node.get("type", "")

            # Boost scores based on node importance
            if node_type == "Indicator":
                score *= 3.0
            elif node_type == "Document":
                score *= 2.5
            elif node_type == "Country":
                score *= 2.0
            elif node_type == "DataColumn":
                score *= 0.8
            elif node_type == "DataTable":
                score *= 0.5

            node["score"] = score
            valid_nodes.append(node)

        return sorted(valid_nodes, key=lambda x: x.get("score", 0), reverse=True)

class ContextAssembly:
    """Assemble context blocks for the LLM."""

    @staticmethod
    def assemble(nodes: List[Dict[str, Any]], max_chars: int = 24000) -> str:
        """Create formatted context string with [Doc_N] labels."""
        blocks = []
        char_count = 0

        for i, node in enumerate(nodes, 1):
            props = node.get("properties", {})
            node_type = node.get("type", "Unknown")

            if node_type == "Indicator":
                block = (f"[Doc_{i}] | Type: Indicator\n"
                         f"Code: {node['id']} | Category: {props.get('category', '')}\n"
                         f"Name: {props.get('name', '')}\n"
                         f"Description: {props.get('description', '')}\n")
            elif node_type == "Country":
                block = (f"[Doc_{i}] | Type: Country\n"
                         f"Code: {node['id']} | Name: {props.get('name', '')}\n"
                         f"Region: {props.get('region', '')} | Income: {props.get('income_group', '')}\n")
            elif node_type == "Document":
                block = (f"[Doc_{i}] | Type: Document\n"
                         f"Title: {props.get('title', '')}\n"
                         f"Content: {props.get('abstract', props.get('text', ''))[:1000]}\n")
            else:
                block = f"[Doc_{i}] | Type: {node_type} | ID: {node['id']}\n"

            blocks.append(block)
            char_count += len(block)
            if char_count > max_chars:
                break

        return "\n".join(blocks)
