# Repository Structure — Intelligent Data Platform (IDP)

> **Status: Phase 1-4 deployed** (2026-05-20). Bootstrap, Ingestion, Transformation, and Orchestration are implemented.
> Phase 5 (Intelligence) and Phase 6 (Hardening) are planned.

---

## 1. Current State

```text
backend/
├── docker-compose.yml               # Unified compose (MinIO + PostgreSQL + Airflow)
├── .env / .env.example               # Environment config (Pydantic BaseSettings)
├── pyproject.toml                    # Project metadata, dependencies, entry points
│
├── docs/                             # Architecture & design documents (source of truth)
│   ├── high-level-architecture.md
│   ├── technology-stack.md
│   ├── data-model.md
│   ├── chatbot-architecture.md
│   ├── environment-config.md
│   ├── source-catalog.md
│   ├── ingestion-manual-runbook.md
│   ├── api-design.md
│   ├── repo-structure.md
│   ├── todos.md
│   └── phases/                       # Per-phase implementation task lists
│       ├── 00-docs-finalization.md
│       ├── 01-bootstrap-storage.md
│       ├── 02-ingestion.md
│       ├── 03-transformation.md
│       ├── 04-orchestration.md
│       ├── 05-intelligence.md
│       ├── 06-hardening.md
│       └── 07-expand.md
│
├── idp/                              # Core Python package (22 files, OOP/SOLID)
│   ├── core/
│   │   ├── config.py                 # Pydantic BaseSettings (zero os.environ.get elsewhere)
│   │   ├── models.py                 # EconomicIndicator, Document, TextChunk dataclasses
│   │   └── logging.py                # Structured logging
│   ├── ingestion/
│   │   ├── base.py                   # AbstractConnector ABC (Template Method)
│   │   ├── services/
│   │   │   └── minio.py              # MinioService (boto3 wrapper)
│   │   └── connectors/
│   │       ├── world_bank/           # WorldBankConnector (wbgapi → Parquet → MinIO)
│   │       └── world_bank_docs/      # WBDocsConnector (WDS API → text chunks → MinIO)
│   │           ├── connector.py, client.py, chunker.py, text_loader.py, wds_client.py
│   ├── transform/
│   │   └── export.py                 # PostgresExportService (DuckDB → PostgreSQL)
│   └── orchestration/
│       └── dag_utils.py              # Shared Airflow utilities (health sensors, secrets)
│
├── orchestration/airflow/
│   ├── dags/                         # 4 DAGs with cross-DAG triggering
│   │   ├── ingest_world_bank.py
│   │   ├── ingest_world_bank_docs.py
│   │   ├── run_dbt_transform.py
│   │   └── export_gold_to_postgres.py
│   └── plugins/__init__.py
│
├── transform/dbt/
│   ├── dbt_project.yml, profiles.yml
│   ├── models/
│   │   ├── staging/                  # stg_world_bank__indicators, docs_metadata, docs_chunks
│   │   └── marts/                    # dim_countries, dim_indicators, dim_dates, fact_economic_indicators
│   ├── seeds/                        # seed_countries.csv, seed_indicators.csv
│   ├── macros/                       # configure_s3.sql, generate_date_dim.sql
│   └── tests/                        # assert_gdp_range.sql, assert_no_future_dates.sql
│
├── infra/
│   ├── docker/airflow/               # Custom Airflow Dockerfile + pre-cached DuckDB extensions
│   └── scripts/                      # minio-init.sh, init-postgres.sql
│
└── tmp/                              # Mounted volumes: DuckDB DB, local parquet cache
    ├── duckdb/idp.db
    ├── world_bank/year=*/data.parquet
    └── world_bank_docs/{metadata,chunks}/
```

---

## 2. Target Directory Structure (Phase 5-6 additions)

The following directories will be added as future phases are implemented:

```text
backend/
├── ...existing structure above...
├── services/                       # (Phase 5) Backend services
│   ├── api/                        # FastAPI endpoints
│   ├── ai/                         # RAG pipeline, LLM logic
│   └── shared/                     # Config, utils, shared clients
├── notebooks/                      # Exploration & prototyping
└── infra/
    └── nginx/                      # (Phase 6) Reverse proxy, SSL
```

---

## 3. Directory Roles

### 3.1 `docs/`
Architecture decisions, stack choices, roadmap, data model, API spec, runbooks. Currently the only active directory — serves as the design source of truth before implementation begins.

### 3.2 `infra/`
Deployment configuration for on-premise infrastructure. Compose files split by activation stage (`bootstrap`, `transform`, `orchestration`, `edge`, `scale`).

### 3.3 `orchestration/`
Pipeline scheduling and workflow logic. Airflow DAGs orchestrate but do not contain business logic — that lives in `ingestion/`, `transform/`, `services/`.

### 3.4 `ingestion/`
Connectors and schemas for bringing data into Bronze (MinIO/Parquet).

### 3.5 `transform/`
All data transformation logic: Bronze → Silver → Gold. DuckDB is the compute engine; dbt-duckdb is the adapter.

### 3.6 `services/`
Backend code for APIs, AI, and shared libraries.

### 3.7 `storage/`
Sample data and schema contracts. Not for production data.

### 3.8 `notebooks/`
Exploration and prototyping. Production logic must move to the appropriate directory once stable.

---

## 4. Mapping: Repo Structure ↔ System Architecture

| Architecture Layer | Primary Directories |
|---|---|
| Layer 1: Ingestion | `ingestion/`, `orchestration/airflow/dags/` |
| Layer 2: Transformation | `transform/dbt/` |
| Layer 3: Serving | `services/api/`, `services/shared/` |
| Layer 4: Intelligence | `services/ai/` |
| Layer 5: Orchestration | `orchestration/airflow/` |
| Infrastructure | `infra/` |
| Documentation | `docs/` |

---

## 5. Implementation Order

### Phase 0 — Docs First ✅
Lock architecture, data model, and tech choices in `docs/` before writing any code.

### Phase 1 — Bootstrap ✅
- `docker-compose.yml` — MinIO + PostgreSQL + bucket init
- `infra/scripts/` — `minio-init.sh`, `init-postgres.sql`
- `idp/core/config.py` — Pydantic BaseSettings

### Phase 2 — Ingestion ✅
- `idp/ingestion/connectors/world_bank/` — WorldBankConnector
- `idp/ingestion/connectors/world_bank_docs/` — WBDocsConnector + text chunking
- `idp/ingestion/services/minio.py` — MinioService

### Phase 3 — Transformation ✅
- `transform/dbt/` — dbt-duckdb project with staging + marts (star schema)
- `idp/transform/export.py` — PostgresExportService (Gold → PostgreSQL)

### Phase 4 — Orchestration ✅
- `orchestration/airflow/dags/` — 4 DAGs with cross-DAG triggering
- `idp/orchestration/dag_utils.py` — Shared utilities
- `infra/docker/airflow/` — Custom Dockerfile + DuckDB extensions

### Phase 5 — Serving & Intelligence (planned)
- `services/api/` — FastAPI endpoints
- `services/ai/` — RAG pipeline, LLM integration

### Phase 6 — Hardening (planned)
- `infra/nginx/` — Reverse proxy (only if external access needed)
- `infra/scripts/` — Backup, health checks
- `orchestration/airflow/tests/` — DAG validation

---

## 6. Placement Conventions

- Airflow DAGs only orchestrate; business logic lives in `ingestion/`, `transform/`, `services/`.
- SQL transform logic belongs in `transform/dbt/`, not embedded in DAGs.
- Shared config and utilities go in `services/shared/`, not scattered across modules.
- Decision docs and data standards go in `docs/` or `storage/contracts/`.
- Notebooks are for experimentation only; stable logic must migrate to production directories.

---

## 7. What NOT to Create Yet

- No `apps/` directory (not in scope for Lean phase — BI/dashboards via Looker Studio in Expand phase).
- No Redis at bootstrap (Phase 1-3); add in Phase 5 for Celery broker + rate limiting.
- No `infra/nginx/` config in bootstrap stage.
- No `infra/monitoring/` (Phase 2 — Prometheus/Grafana).
- No CI/CD layout before initial code scaffolding is done.
