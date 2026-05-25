# Intelligent Data Platform (IDP)

Data platform for economic indicators — ingestion, transformation, serving, and AI-powered querying.

> **Status: Design / Blueprint.** Implementation pending. All architecture docs are in `backend/docs/`.

## Quick Start

```bash
git clone <repo-url>
cd data-platform-intelligent

# Read the architecture
cat backend/docs/high-level-architecture.md

# Start from Phase 0
cat backend/docs/todos.md
```

## Architecture Overview

```
Data Sources → Ingestion (Python) → Bronze (MinIO/Parquet) → Silver (DuckDB+dbt) → Gold (PostgreSQL+pgvector) → API (FastAPI) → AI (Graph-Augmented RAG)
                                                                                              ↑
                                                                                    Airflow 3.0 orchestrates
```

**5-layer Lean Data Stack:**

| Layer | Technology | Phase |
|---|---|---|
| 1. Ingestion | Python (requests, pandas, wbgapi) | 2 |
| 2. Transformation | DuckDB + dbt-core | 3 |
| 3. Serving | PostgreSQL 16 + pgvector | 3/5 |
| 4. Intelligence | Graph-Augmented RAG (Neo4j + Elasticsearch + Gemini) | 5 |
| 5. Orchestration | Apache Airflow 3.0 | 4 |

**Infrastructure:** Docker Compose on Ubuntu 22.04 (16GB RAM / 512GB SSD).

## Documentation

All design docs live in [`backend/docs/`](backend/docs/):

| Document | Description |
|---|---|
| [high-level-architecture.md](backend/docs/high-level-architecture.md) | 5-layer model, design decisions, cost estimate |
| [technology-stack.md](backend/docs/technology-stack.md) | Full tech stack per layer, activation guide |
| [data-model.md](backend/docs/data-model.md) | Bronze/Silver/Gold schemas, star schema, ERD |
| [chatbot-architecture.md](backend/docs/chatbot-architecture.md) | 14-step Graph-Augmented RAG pipeline |
| [environment-config.md](backend/docs/environment-config.md) | Docker Compose, env vars, resource limits |
| [source-catalog.md](backend/docs/source-catalog.md) | Data sources, indicators, API docs |
| [ingestion-manual-runbook.md](backend/docs/ingestion-manual-runbook.md) | Manual connector runbook |
| [repo-structure.md](backend/docs/repo-structure.md) | Directory layout (current + target) |
| [todos.md](backend/docs/todos.md) | Master task list across all phases |
| [api-design.md](backend/docs/api-design.md) | API endpoints, request/response schemas |
| [phases/](backend/docs/phases/) | Per-phase implementation checklists |

## Phases

| Phase | Content | Duration | Status |
|---|---|---|---|
| 0 | Docs Finalization | Done | ✅ |
| 1 | Bootstrap Storage (MinIO) | 1.5–2 days | Pending |
| 2 | Ingestion (World Bank connectors) | ~3 days | Pending |
| 3 | Transformation (DuckDB + dbt) | ~11-13 days | Pending |
| 4 | Orchestration (Airflow) | ~5-6 days | Pending |
| 5 | Serving & Intelligence (API + RAG) | ~16-20 days | Pending |
| 6 | Hardening | ~5-6 days | Pending |
| **Total Lean** | | **~42-52 days** | |

## Principles

- **Basic first, modern later** — get end-to-end working, optimize after
- **Lean stack** — fewest tools possible, each must justify its value
- **Open-source first** — no vendor lock-in, no license fees
- **Single-node first** — max out 16GB/512GB before scaling to cloud
- **Docs-first** — design decisions locked in docs before code
