# TODO List — Intelligent Data Platform (IDP)

> **Status: Reset — Docs-first restart (2026-05-18)**
>
> All previous source code has been removed. The `docs/` directory now serves as the sole design blueprint.
> Implementation will restart from these docs, phased incrementally.
>
> **Chi tiết từng phase:** xem [`docs/phases/`](phases/) — mỗi phase có file riêng với checklist cụ thể.
>
> Strategy: "Docs first, basic next, modern later"
> Difficulty: 🟢 Easy | 🟡 Medium | 🔴 Hard

---

## Phase 0: Docs Finalization (Current)

> Goal: Ensure all design docs are internally consistent and complete before any code is written.

| # | Task | Difficulty | Estimate | Status |
|---|---|---|---|---|
| 0.1 | Review all docs for consistency and completeness | 🟢 | Done | ✅ |
| 0.2 | Fix cross-references between docs | 🟢 | Done | ✅ |
| 0.3 | Finalize data model (star schema, medallion layers) | 🟢 | Done | ✅ |
| 0.4 | Finalize source catalog (data sources, indicators) | 🟢 | Done | ✅ |
| 0.5 | Finalize technology choices per phase | 🟢 | Done | ✅ |

---

## Phase 1: Bootstrap Storage (~2 days) ✅

> Goal: Start only the services needed to ingest and inspect raw data.

| # | Task | Difficulty | Estimate | Status |
|---|---|---|---|---|
| 1.1 | Write bootstrap compose for MinIO (+ bucket init) | 🟡 | 0.5 day | ✅ |
| 1.2 | Configure `.env` + secrets | 🟢 | 0.5 day | ✅ |
| 1.3 | Validate MinIO buckets (`bronze`, `silver`, `artifacts`) | 🟢 | 0.25 day | ✅ |
| 1.4 | Smoke test manual upload/read path | 🟢 | 0.25 day | ✅ |
| 1.5 | Document startup/shutdown workflow | 🟢 | 0.25 day | ✅ |

**Subtotal: ~1.5-2 days**

---

## Phase 2: Ingestion — Manual First (~3 days) ✅

> Goal: Raw data (Parquet) lands in MinIO before introducing orchestration.

| # | Task | Difficulty | Estimate | Status |
|---|---|---|---|---|
| 2.1 | World Bank connector (wbgapi → Parquet → MinIO) | 🟢 | 0.5 day | ✅ |
| 2.2 | World Bank Docs connector (WDS API → Parquet) | 🟡 | 1 day | ✅ |
| 2.3 | World Bank Docs text extraction + chunking (server-side `/text/` endpoint) | 🟡 | 1 day | ✅ |
| 2.4 | Manual runbook for each connector | 🟢 | 0.5 day | ✅ |

**Subtotal: ~3 days** (scoped to World Bank only initially)

---

## Phase 3: Transformation — DuckDB + dbt (~13-15 days) ✅

> Goal: Clean data in PostgreSQL (Gold), with tests and docs.

### 3.1 Warehouse Bootstrap

| # | Task | Difficulty | Estimate | Status |
|---|---|---|---|---|
| 3.1.1 | Add PostgreSQL compose/profile for Gold | 🟢 | 0.5 day | ✅ |
| 3.1.2 | Enable pgvector + create base schemas | 🟢 | 0.5 day | ✅ |

### 3.2 dbt Project Setup

| # | Task | Difficulty | Estimate | Status |
|---|---|---|---|---|
| 3.2.1 | Init dbt project (`dbt-duckdb` adapter) | 🟢 | 0.5 day | ✅ |
| 3.2.2 | Configure DuckDB to read Parquet from MinIO (S3) | 🟡 | 1 day | ✅ |
| 3.2.3 | Design schema Bronze → Silver → Gold | 🟡 | 1.5 days | ✅ |

### 3.3 dbt Models

| # | Task | Difficulty | Estimate | Status |
|---|---|---|---|---|
| 3.3.1 | Staging models: World Bank indicators | 🟡 | 1 day | ✅ |
| 3.3.2 | Staging models: World Bank Docs (chunks) | 🟡 | 0.5 day | ✅ |
| 3.3.3 | Mart: `dim_countries`, `dim_indicators`, `dim_dates` | 🟡 | 1 day | ✅ |
| 3.3.4 | Mart: `fact_economic_indicators` | 🟡 | 1.5 days | ✅ |
| 3.3.5 | Export Gold → PostgreSQL | 🟡 | 1 day | ✅ |

### 3.4 Data Quality & Docs

| # | Task | Difficulty | Estimate | Status |
|---|---|---|---|---|
| 3.4.1 | dbt tests: `not_null`, `unique`, `accepted_values` | 🟢 | 1 day | ✅ |
| 3.4.2 | Custom tests: business logic (GDP range, CPI bounds) | 🟡 | 1 day | ✅ |
| 3.4.3 | Generate dbt docs | 🟢 | 0.5 day | ✅ |

**Subtotal: ~11-13 days**

---

## Phase 4: Operationalize with Airflow (~5-6 days) ✅

> Goal: Add scheduling only after manual connector/dbt runs are stable.

| # | Task | Difficulty | Estimate | Status |
|---|---|---|---|---|
| 4.1 | Deploy Airflow 3.0 (LocalExecutor) | 🟡 | 1 day | ✅ |
| 4.2 | Configure PostgreSQL metadata DB | 🟢 | 0.5 day | ✅ |
| 4.3 | DAG: `ingest_world_bank` (monthly) | 🟢 | 0.5 day | ✅ |
| 4.4 | DAG: `ingest_world_bank_docs` (monthly) | 🟢 | 0.5 day | ✅ |
| 4.5 | DAG: `run_dbt_transform` (daily) | 🟡 | 1 day | ✅ |
| 4.6 | DAG: `export_gold_to_postgres` | 🟢 | 0.5 day | ✅ |
| 4.7 | Error handling + retry + alerting baseline | 🟡 | 1 day | ✅ |

**Subtotal: ~5-6 days**

---

## Phase 5: Serving & Intelligence (~16-20 days)

> Goal: API serves data; AI can answer complex economic questions via Graph-Augmented RAG.
>
> Economic data is inherently graph-structured — indicators relate to each other, countries cluster by region/income, and data lineage traces metrics back to sources. A pure vector/RAG approach would fail on structural reasoning. The full graph-augmented pipeline is required from the start.

### 5.1 API Setup

| # | Task | Difficulty | Estimate |
|---|---|---|---|
| 5.1.1 | Setup FastAPI project structure | 🟢 | 0.5 day |
| 5.1.2 | API endpoints: query economic indicators | 🟡 | 1 day |
| 5.1.3 | API endpoints: search/filter data | 🟡 | 1 day |

### 5.2 Search Infrastructure

| # | Task | Difficulty | Estimate |
|---|---|---|---|
| 5.2.1 | Setup Elasticsearch for lexical metadata search | 🟡 | 1.5 days |
| 5.2.2 | Setup pgvector for semantic search | 🟢 | 0.5 day |
| 5.2.3 | Index economic indicators + documents metadata | 🟡 | 1 day |

### 5.3 Graph Infrastructure (Neo4j)

| # | Task | Difficulty | Estimate |
|---|---|---|---|
| 5.3.1 | Deploy Neo4j + design graph schema | 🟡 | 1 day |
| 5.3.2 | Build data lineage graph (tables, columns, indicators) | 🔴 | 3 days |
| 5.3.3 | Build economic relationship graph (country clusters, indicator categories) | 🟡 | 1.5 days |

### 5.4 Graph-Augmented RAG Pipeline (14-step)

| # | Task | Difficulty | Estimate |
|---|---|---|---|
| 5.4.1 | Pre-processing & Anchor Discovery (steps 1-4) | 🟡 | 2 days |
| 5.4.2 | Graph Expansion via Neo4j traversal (step 5) | 🔴 | 2 days |
| 5.4.3 | Filtering & Context Assembly (steps 6-8) | 🟡 | 1.5 days |
| 5.4.4 | LLM Generation & Post-processing (steps 9-11) | 🟡 | 2 days |
| 5.4.5 | Delivery: WebSocket dual-channel streaming (steps 12-14) | 🟡 | 2 days |

### 5.5 Airflow Integration

| # | Task | Difficulty | Estimate |
|---|---|---|---|
| 5.5.1 | DAG: `refresh_embeddings` (after dbt run) | 🟡 | 1 day |
| 5.5.2 | DAG: `refresh_graph_index` (after gold export) | 🟡 | 1 day |

**Subtotal: ~16-20 days**

---

## Phase 6: Hardening (~5-6 days)

> Goal: Production readiness — backup, security, monitoring.

| # | Task | Difficulty | Estimate |
|---|---|---|---|
| 6.1 | Docker resource limits tuning | 🟡 | 0.5 day |
| 6.2 | PostgreSQL RBAC (roles per service) | 🟡 | 0.5 day |
| 6.3 | Backup script (`pg_dump` → local) | 🟡 | 0.5 day |
| 6.4 | Security review (ports, credentials) | 🟡 | 0.5 day |
| 6.5 | Nginx reverse proxy (only if external access needed) | 🟡 | 0.5 day |
| 6.6 | Prometheus + Grafana (only if monitoring needed) | 🟡 | 2 days |
| 6.7 | Documentation: operations runbook | 🟢 | 1 day |

**Subtotal: ~5-6 days**

---

## Phase Summary

| Phase | Content | Duration | Status |
|---|---|---|---|
| Phase 0 | Docs Finalization | Done | ✅ |
| Phase 1 | Bootstrap Storage | 1.5–2 days | ✅ |
| Phase 2 | Ingestion (manual first) | ~3 days | ✅ |
| Phase 3 | Transformation (DuckDB + dbt) | ~11-13 days | ✅ |
| Phase 4 | Operationalize with Airflow | ~5-6 days | ✅ |
| Phase 5 | Serving & Intelligence (API + Graph-Augmented RAG) | ~16-20 days | ✅ |
| Phase 6 | Hardening | ~5-6 days | ⏳ |
| **Total Lean** | | **~42-52 days (~2.5 months)** | **5/6 done** |

---

## Expand Phase — After Lean is Validated

> Only deploy when Lean phase is running and validated.

| # | Task | Difficulty | Trigger |
|---|---|---|---|
| E.1 | Add more data sources (NSO, FRED) | 🟡 | Core pipeline stable |
| E.2 | GCS backup | 🟡 | Production readiness |
| E.3 | BigQuery integration | 🟡 | Data > few GB |
| E.4 | Looker Studio dashboards | 🟡 | External stakeholders |
| E.5 | CeleryExecutor for distributed tasks | 🟡 | DAGs running slow |
| E.6 | ML models (XGBoost, Prophet) | 🟡 | Need forecasting |
| E.7 | CI/CD pipeline | 🟡 | Team collaboration |
| E.8 | SSL + Cloudflare Tunnel | 🟡 | Internet exposure |

---

## Notes

- Estimates based on **1 full-time developer** (data engineer).
- Docs are the source of truth — all implementation should reference them.
- Start with MinIO only; add PostgreSQL, Airflow, and other services incrementally.
- DuckDB + dbt is the heart of the pipeline — invest time here.
- Graph-Augmented RAG (Neo4j + Elasticsearch + pgvector) is the core intelligence approach — economic data demands graph-based reasoning from the start.
- Redis is a Phase 5 dependency (Celery broker for RAG pipeline), not needed before.
- With 2 people: Lean shrinks to ~1-1.5 months.
- Buffer ~15% for learning curve and unexpected issues.
