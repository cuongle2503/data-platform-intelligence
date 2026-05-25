# Chatbot Architecture — Intelligent Data Platform (IDP)

> **Status: Design / Blueprint**. Target architecture for the AI/chatbot module. Implementation pending.
>
> Economic data is inherently graph-structured — indicators relate to each other, countries cluster by region and income group, and data lineage traces dashboard metrics back to raw sources. A pure vector/RAG approach cannot reason about these structural relationships. Graph-Augmented RAG (Neo4j + pgvector + Elasticsearch) is the required approach from the start.

## Overview
The chatbot module for the Intelligent Data Platform uses a deterministic, hard-coded imperative workflow (Graph-Augmented RAG Pipeline) rather than an Agentic RAG approach. This ensures absolute control, high reliability, zero hallucination, and predictable performance, making it highly suitable for enterprise data.

## 1. System Architecture

- **Framework:** FastAPI (Python) - High performance, native async/await, excellent for WebSocket streaming.
- **Database:** PostgreSQL - For user management, sessions, and chat history.
- **Graph DB:** Neo4j - The "game-changer" component used to traverse Data Lineage (e.g., how a column in a dashboard maps back to raw tables).
- **Search Engine:** Elasticsearch - For precise keyword matching of metadata (table names, column names).
- **Vector DB:** pgvector - For semantic search of data definitions and documentation.
- **Cache & Queue:** Redis + Celery - For rate limiting and background tasks.

## 2. 14-Step Graph-Augmented RAG Pipeline

The pipeline processes user queries sequentially:

### PRE-PROCESSING & ANCHOR DISCOVERY
1. **Query Expansion:** Normalizes user input, corrects typos, and maps business jargon to actual data terms.
2. **Elasticsearch (Lexical Search):** Finds precise matches for exact metadata (e.g., indicator `NY.GDP.MKTP.CD`, table `fact_economic_indicators`).
3. **Vector DB (Semantic Search):** Finds semantic matches for the user's intent.
4. **RRF Fusion:** Combines lexical and semantic results using Reciprocal Rank Fusion to identify the "Top 20 Anchor Nodes".

### GRAPH EXPANSION (NEO4J)
5. **Graph Traversal:** Uses the 20 Anchor Nodes as entry points into Neo4j. Traverses the data lineage network (parents, children, foreign keys) to expand the context to ~100 related data assets.

### FILTERING & CONTEXT ASSEMBLY
6. **Version Filter:** Removes deprecated, outdated, or inactive tables/views.
7. **Data Hierarchy Re-rank:** Boosts the ranking of Certified/Gold data over Bronze/Silver or ad-hoc data.
8. **Assembly:** Formats the final list of nodes into a structured context, injecting strict labels like `[Doc_1]`, `[Doc_2]`.

### LLM GENERATION & POST-PROCESSING
9. **Generation:** Prompts the LLM (Gemini 2.0 Flash for fast Q&A, Gemini 2.5 Pro for complex multi-step reasoning) using a strict system prompt that *requires* referencing the provided `[Doc_N]` labels.
10. **Citation Verification:** A Regex-based verify step checks if the generated `[Doc_N]` tags actually exist in the context. If not, it forces a retry.
11. **Disclaimer Injection:** Appends necessary legal/reference disclaimers (e.g., "Data is for reference only").

### DELIVERY & PERSISTENCE
12. **WebSocket Dual-Channel Streaming:** Streams tokens back to the UI with minimal delay (e.g., 50ms) for a smooth typing effect, with a REST fallback to prevent data loss.
13. **Persistence:** Saves the full chat history, context citations, and credit/token usage to PostgreSQL.
14. **Background Tasks:** Offloads non-critical tasks (generating chat titles, suggesting follow-up questions) to Celery workers.

## 3. Embedding Model

- **Model:** `text-embedding-004` (Google Gemini Embeddings)
- **Dimension:** 768
- **Usage:** Embed indicator metadata (name, category, description) and document chunks for semantic search via pgvector.
- **Cost:** Included in Gemini API pricing (~$0.000025 per 1K chars).

---

## 4. LLM Security Considerations

| Concern | Mitigation |
|---|---|
| Prompt injection via user query | Strict system prompt with role boundaries; input sanitization; query length limits (max 1000 chars) |
| Sensitive data in prompts | No PII or proprietary data is sent — only public economic indicators and document metadata |
| Citation manipulation | Regex verification step (Step 10) validates all `[Doc_N]` tags against actual context |
| API key exposure | `GEMINI_API_KEY` stored in `.env` (gitignored), never logged |
| Token cost abuse | Per-user daily quota caps; rate limiting via Redis in Phase 5 |
| Hallucination risk | Deterministic pipeline with strict `[Doc_N]` citation requirement; fallback disclaimer when confidence is low |

---

## 5. Why Neo4j over PostgreSQL for the Graph Step?
While simpler pipelines might use recursive CTEs in PostgreSQL (like LEXcentra), a Data Platform involves deep and complex Data Lineage networks. Neo4j is specifically designed to perform deep multi-hop traversals in milliseconds, allowing the chatbot to instantly discover that a dashboard metric depends on 5 different underlying dimension tables.