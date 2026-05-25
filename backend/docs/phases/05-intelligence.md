# Phase 5: Serving & Intelligence — Graph-Augmented RAG

> **Status: Completed | Duration: ~16-20 ngày | Core của AI layer**

---

## Mục tiêu

FastAPI phục vụ REST API + WebSocket. Hệ thống Graph-Augmented RAG 14 bước: Elasticsearch (lexical) + pgvector (semantic) + Neo4j (graph) → Gemini trả lời câu hỏi kinh tế có citation.

---

## 5.1 FastAPI project setup (0.5 ngày)

- [x] 5.1.1 Tạo `services/api/main.py`
  - FastAPI app với lifespan: startup/shutdown
  - CORS middleware (allow local dev origins)
  - Health endpoint `GET /health` → `{"status": "ok"}`
  - OpenAPI docs tại `/docs`

- [x] 5.1.2 Tạo `services/shared/config.py`
  - Load từ `.env`: DATABASE_URL, MINIO_*, NEO4J_URI, ES_HOST, REDIS_URL, GEMINI_API_KEY
  - Pydantic Settings class

- [x] 5.1.3 Tạo `services/shared/database.py`
  - asyncpg connection pool cho PostgreSQL
  - Dependency `get_db()` inject vào FastAPI routes

- [x] 5.1.4 Tạo `services/shared/logging.py`
  - structlog setup: JSON format, timestamp, level

- [x] 5.1.5 Verify
  - `uvicorn services.api.main:app --reload` → health endpoint trả 200

---

## 5.2 Indicator API endpoints (2 ngày)

- [x] 5.2.1 Tạo `services/api/models/schemas.py`
  - Pydantic model `IndicatorResponse`: indicator_code, indicator_name, country, year, value, category
  - Pydantic model `IndicatorQuery`: country_code, indicator_codes (list, optional), start_year, end_year
  - Pydantic model `SearchQuery`: q (string), limit (int)

- [x] 5.2.2 Tạo `services/api/routers/indicators.py`
  - `GET /api/indicators?country_code=VNM&start_year=2020&end_year=2024`
    - Query PostgreSQL `gold.fact_economic_indicators` JOIN dimensions
    - Trả list IndicatorResponse
  - `GET /api/indicators/{indicator_code}?country_code=all`
    - Trả time series cho 1 indicator
  - `GET /api/countries` → list dim_countries
  - `GET /api/indicators/list` → list dim_indicators với categories

- [x] 5.2.3 Test endpoints
  - Gọi từng endpoint, verify JSON response
  - Test edge cases: country không tồn tại, year ngoài range
  - Test performance: response < 100ms cho các query cơ bản

- [x] 5.2.4 Tạo `services/api/routers/search.py`
  - `GET /api/search?q=GDP+Vietnam&limit=10`
  - Search trong Elasticsearch + pgvector (xây sau ở 5.3-5.4)

---

## 5.3 Elasticsearch setup & indexing (1.5 ngày)

- [x] 5.3.1 Thêm Elasticsearch vào compose
  - service `elasticsearch`:
    - image `elasticsearch:8.17.0`
    - env `discovery.type=single-node`, `xpack.security.enabled=false`
    - port `9200:9200`
    - resource limit: 2GB mem, 1 CPU
    - healthcheck `curl http://localhost:9200/_cluster/health`
    - **Lưu ý:** single-node nghĩa là không có redundancy — nếu ES down, lexical search fail. Chấp nhận được cho Lean phase.

- [x] 5.3.2 Tạo index mapping `services/ai/elasticsearch/es_mappings.py`
  - Index `indicators`: columns code, name, category, country, year
  - Index `documents`: columns title, abstract, doc_type, countries, topics

- [x] 5.3.3 Tạo `services/ai/elasticsearch/es_indexer.py`
  - Đọc từ PostgreSQL Gold → bulk index vào ES
  - Đọc từ MinIO documents metadata → bulk index vào ES
  - Log progress từng batch

- [x] 5.3.4 Tạo `services/ai/elasticsearch/es_search.py`
  - Hàm `lexical_search(query, index, size=20)` → multi_match query
  - Trả list dict: id, score, source

- [x] 5.3.5 Run indexer → verify `GET /es-index/_search?q=GDP` có kết quả

---

## 5.4 pgvector embeddings (1 ngày)

- [x] 5.4.1 Tạo `services/ai/embeddings/embedder.py`
  - Hàm `embed_texts(texts)` → gọi Gemini Embeddings API → trả list[list[float]]
  - Embed indicator metadata: `{name} - {category} - {description}`
  - Embed document chunks: chunk text

- [x] 5.4.2 Tạo `services/ai/embeddings/indexer.py`
  - Bảng `embeddings.economic_embeddings`:
    - id, source_type (indicator/document), source_id, chunk_id, embedding (vector(768)), metadata (jsonb)
  - Bulk INSERT embeddings vào PostgreSQL
  - Tạo IVFFlat index trên column embedding (chỉ build index khi có > 1000 rows, nếu ít hơn thì sequential scan vẫn đủ nhanh)

- [x] 5.4.3 Tạo `services/ai/embeddings/vector_search.py`
  - Hàm `semantic_search(query, top_k=20)`:
    - Embed query → `SELECT ... ORDER BY embedding <=> query_embedding LIMIT top_k`
    - Trả list với score + metadata

- [x] 5.4.4 Test
  - Index 1000 indicators + chunks
  - Search "inflation in Vietnam" → top results có indicator CPI

---

## 5.5 Neo4j graph setup (2 ngày)

- [x] 5.5.1 Thêm Neo4j vào compose
  - service `neo4j`:
    - image `neo4j:5-community`
    - ports `7474:7474`, `7687:7687`
    - env `NEO4J_AUTH=neo4j/<password>`
    - volume `neo4j_data:/data`, `neo4j_logs:/logs`
    - resource limit: 2GB mem, 1 CPU

- [x] 5.5.2 Design graph schema `services/ai/graph/schema.py`
  - Node labels: `Country`, `Indicator`, `IndicatorCategory`, `DataTable`, `DataColumn`, `Dashboard`, `Document`, `DocTopic`
  - Relationships:
    - `(:Country)-[:HAS_INDICATOR]->(:Indicator)`
    - `(:Indicator)-[:BELONGS_TO]->(:IndicatorCategory)`
    - `(:Indicator)-[:SOURCED_FROM]->(:DataTable)`
    - `(:DataTable)-[:CONTAINS]->(:DataColumn)`
    - `(:DataColumn)-[:DERIVED_FROM]->(:DataColumn)`
    - `(:Dashboard)-[:USES]->(:DataColumn)`
    - `(:Document)-[:ABOUT]->(:Country)`
    - `(:Document)-[:TAGGED]->(:DocTopic)`

- [x] 5.5.3 Tạo `services/ai/graph/builder.py`
  - Tạo constraints + indexes: `CREATE CONSTRAINT FOR ...`
  - Ingest countries: `MERGE (c:Country {code: $code, name: $name, region: $region})`
  - Ingest indicators: `MERGE (i:Indicator {code: $code, name: $name, category: $cat})`
  - Ingest data lineage: `(:Indicator)-[:SOURCED_FROM]->(:DataTable {name: 'raw_world_bank_indicators'})`
  - `(:DataTable)-[:CONTAINS]->(:DataColumn)` cho từng column trong data model
  - Ingest documents: `MERGE (d:Document {doc_id: $id})`
  - Link documents → countries: `MATCH (d:Document), (c:Country) WHERE c.code IN d.countries CREATE (d)-[:ABOUT]->(c)`

- [x] 5.5.4 Tạo `services/ai/graph/traversal.py`
  - Hàm `expand_context(anchor_nodes)`:
    - Start từ anchor nodes → expand 2-3 hops theo tất cả relationships
    - Collect đến khi đạt ~100 nodes
    - Trả list dict: {type, id, properties, relationships}

- [x] 5.5.5 Verify
  - Neo4j browser `http://<server>:7474` → thấy nodes, relationships
  - `MATCH (c:Country) RETURN c` → 10 countries
  - `MATCH (c:Country)-[:HAS_INDICATOR]->(i:Indicator) RETURN c, i LIMIT 10`

---

## 5.6 RAG Pipeline — Steps 1-4: Anchor Discovery (2 ngày)

- [x] 5.6.1 Tạo `services/ai/pipeline/query_expansion.py`
  - Dict map business terms → technical terms (vd: "lạm phát" → "inflation, CPI")
  - Hàm `expand_query(raw_query)` → list of search phrases

- [x] 5.6.2 Tạo `services/ai/pipeline/rrf_fusion.py`
  - Input: results từ ES (ranked) + results từ pgvector (ranked)
  - RRF score = SUM(1 / (k + rank_i)) với k=60
  - Output: merged list sorted by RRF score, lấy top 20

- [x] 5.6.3 Kết nối steps 1-4
  - Query Expansion → [ES search + Vector search song song] → RRF Fusion → Top 20 Anchor Nodes

- [x] 5.6.4 Unit test từng step
  - Test query expansion với input khác nhau
  - Test RRF fusion với mock results

---

## 5.7 RAG Pipeline — Step 5: Neo4j Graph Expansion (2 ngày)

- [x] 5.7.1 Tạo `services/ai/pipeline/graph_traversal.py`
  - Input: 20 anchor nodes → build Cypher query
  - Traversal logic:
    - START từ anchor indicator nodes
    - MATCH (i)-[:BELONGS_TO]->(cat) → thêm category nodes
    - MATCH (i)-[:SOURCED_FROM]->(t)-[:CONTAINS]->(col) → thêm lineage
    - MATCH (col)-[:DERIVED_FROM*1..3]->(upstream_col) → recursive lineage
    - MATCH (anchor_country)-[:HAS_INDICATOR]->(related_i) → related indicators
    - MATCH (d:Document)-[:ABOUT]->(anchor_country) → relevant documents
  - Collect tối đa ~100 nodes, deduplicate

- [x] 5.7.2 Test
  - Input: anchor node "GDP indicator, Vietnam"
  - Output: ~100 nodes bao gồm related indicators, data lineage, documents

---

## 5.8 RAG Pipeline — Steps 6-8: Filtering & Assembly (1.5 ngày)

- [x] 5.8.1 Tạo `services/ai/pipeline/filter_rerank.py`
  - Step 6 (Version Filter): remove nodes có `is_deprecated=true` hoặc `is_active=false`
  - Step 7 (Hierarchy Re-rank): boost Gold (×3), Silver (×2), Bronze (×1)
  - Sort nodes theo boosted score

- [x] 5.8.2 Tạo `services/ai/pipeline/context_assembly.py`
  - Format mỗi node → text block:
    ```
    [Doc_1] | Type: Indicator | Source: World Bank
    Name: GDP (current US$)
    Code: NY.GDP.MKTP.CD | Category: gdp
    Description: Gross Domestic Product at current USD
    ```
  - Giới hạn context window ~8K tokens (nếu Gemini Flash)
  - Truncate smart: ưu tiên nodes có score cao, giữ nguyên văn bản

- [x] 5.8.3 Unit test
  - Test với mock nodes → output context có đúng định dạng `[Doc_N]`

---

## 5.9 RAG Pipeline — Steps 9-11: LLM + Post-process (2 ngày)

- [x] 5.9.1 Tạo `services/ai/prompts/system_prompt.txt`
  - Role: Data analyst assistant cho economic data platform
  - Rule: MUST cite sources using `[Doc_N]` labels
  - Rule: Nếu không chắc chắn → "Based on available data, ..."
  - Rule format: Trả lời tiếng Việt, giữ nguyên indicator codes

- [x] 5.9.2 Tạo `services/ai/pipeline/llm_generation.py`
  - Hàm `generate_response(context, user_query, model)`:
    - Gọi Gemini API với system prompt + context + user query
    - model mặc định = `gemini-2.0-flash`
    - Nếu query phức tạp → route sang `gemini-2.5-pro` (dựa trên keyword)
    - Streaming response

- [x] 5.9.3 Tạo citation verification
  - Regex extract tất cả `[Doc_N]` từ response
  - Verify từng Doc_N tồn tại trong context
  - Nếu citation sai → retry (max 3 lần) với error message injected vào prompt

- [x] 5.9.4 Disclaimer injection
  - Append "\n\n---\n*Dữ liệu từ World Bank, cập nhật gần nhất: {date}. Chỉ mang tính tham khảo.*"

---

## 5.10 RAG Pipeline — Steps 12-14: Delivery (2 ngày)

- [x] 5.10.1 Tạo `services/api/routers/chat.py`
  - WebSocket endpoint `ws /api/chat`
  - Nhận query từ client → gọi pipeline → stream tokens từng chunk (50ms interval)
  - JSON message format: `{"type": "token", "data": "..."}` / `{"type": "done"}` / `{"type": "error", "message": "..."}`

- [x] 5.10.2 REST fallback endpoint `POST /api/chat`
  - Nhận `{"query": "...", "stream": false}` → trả full response + citations

- [x] 5.10.3 Persistence
  - Lưu chat session vào PostgreSQL: `chat_sessions` (id, user_id, created_at)
  - Lưu messages: `chat_messages` (id, session_id, role, content, citations jsonb, tokens_used)
  - Lưu token usage để track cost

- [x] 5.10.4 Redis + Celery setup
  - Thêm `redis` + `celery_worker` vào compose
  - Celery task: `generate_chat_title(session_id)` → gọi Gemini tóm tắt title
  - Celery task: `suggest_follow_up(session_id, last_query)` → generate 3 follow-up questions

---

## 5.11 Pipeline orchestrator (1 ngày)

- [x] 5.11.1 Tạo `services/ai/pipeline/orchestrator.py`
  - Class `GraphAugmentedRAG`:
    - `async def process_query(user_query, model, stream)` → chạy 14 steps tuần tự
    - Step timing: log thời gian mỗi step
    - Error handling: nếu 1 step fail → graceful degradation (vd: Neo4j fail → fallback to vector-only, có warning)

- [x] 5.11.2 Inject orchestrator vào FastAPI
  - Tạo singleton RAG instance trong app lifespan
  - Inject vào chat router qua dependency

- [x] 5.11.3 Integration test
  - Query mẫu: "GDP của Việt Nam năm 2023 là bao nhiêu?"
  - Verify response có `[Doc_N]` citations
  - Verify response liên quan đến câu hỏi
  - Verify latency < 5s cho câu hỏi đơn giản

---

## 5.12 Airflow DAGs cho intelligence (1 ngày)

- [x] 5.12.1 Tạo `orchestration/airflow/dags/refresh_embeddings.py`
  - Trigger: sau `export_gold_to_postgres` hoàn thành
  - Task: re-index indicators + documents vào Elasticsearch
  - Task: re-embed indicators + documents → pgvector

- [x] 5.12.2 Tạo `orchestration/airflow/dags/refresh_graph_index.py`
  - Trigger: sau gold export
  - Task: rebuild Neo4j graph (MERGE nodes/relationships)
  - Verify: đếm node count trước/sau

---

## Tổng: 63 checklist items | ~16-20 ngày

**Next: [Phase 6 — Hardening](06-hardening.md)**
