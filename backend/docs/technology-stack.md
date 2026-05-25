# Technology Stack — Intelligent Data Platform (IDP)

> **Status: Design / Blueprint**. Target technology stack — implementation pending.
> Strategy: "Basic first, modern later"
> Split into 2 tiers: Lean target stack and Extended stack

---

## Stack Overview by Layer

| Layer | Lean Target Stack | Start Phase | Extended Tools (Phase 2+) |
|---|---|---|---|
| 1. Ingestion | Python (requests, pandas) | 2 | Pub/Sub, Dataflow (nếu cần real-time) |
| 2. Storage (Raw) | MinIO + Parquet files | 1 | GCS, BigQuery |
| 3. Transformation | DuckDB + dbt-core | 3 | dbt-postgres, Spark/Dataproc |
| 4. Serving | PostgreSQL 16 + pgvector | 3 for PostgreSQL, 5 for active vector use | BigQuery (analytics), Redis |
| 5. Orchestration | Airflow 3.0 | 4 | CeleryExecutor, Prometheus/Grafana |
| Intelligence | Custom Graph-Augmented RAG + LLM APIs | 5 | Agentic AI, MLOps, MLflow |
| Presentation | FastAPI | 5 | Looker Studio (BI) |

---

## Activation Guide

The tables below describe the Lean target stack, but services should be activated gradually.

| Tool / Service | Start When | Why |
|---|---|---|
| MinIO | Immediately | Bronze storage is needed from the first ingestion script |
| DuckDB + dbt | When transform work starts | Core of Bronze → Silver → Gold |
| PostgreSQL + pgvector | When Gold export or API/RAG starts | Serving layer, not required for raw-only ingestion |
| Airflow | When scheduling/retries/manual runs become painful | Operationalization step, not day-1 requirement |
| FastAPI | When consumers need stable endpoints | Serving/API phase |
| Graph RAG pipeline + LLM APIs | When basic data pipeline is already trustworthy | RAG builds on clean data |
| Redis | When cache, sessions, or distributed execution are truly needed | Avoid idle memory usage early |

---

## 1. Ingestion Layer

### Core (Phase 1)

| Technology | Version | Role | License |
|---|---|---|---|
| Python | 3.11+ | Primary language for all ingestion scripts | Free |
| requests / httpx | Latest | HTTP client for API calls | Free |
| pandas | 2.x | Data manipulation, CSV/Excel parsing | Free |
| wbgapi | Latest | World Bank Open Data connector | Free |

### Extended (Phase 2+)

| Technology | Version | Role | License |
|---|---|---|---|
| Google Pub/Sub | Managed | Real-time event streaming | Pay-per-use |
| Google Dataflow | Managed | Stream processing | Pay-per-use |

### Connector Details

| Data Source | Connector | Frequency | Phase |
|---|---|---|---|
| World Bank Open Data | Python (wbgapi) | Monthly | 1 |
| NSO Vietnam | Python (requests) | Monthly | Expand |
| FRED (US Fed) | Python (fredapi) | Weekly | Expand |
| File uploads (CSV, Excel) | Python → MinIO | On-demand | 1 |

---

## 2. Storage Layer (Raw)

### Core (Phase 1)

| Technology | Version | Role | License |
|---|---|---|---|
| MinIO | Latest | S3-compatible object storage for raw files | Free (OSS) |
| Parquet format | — | Columnar storage, 5-10x smaller than CSV | — |

### Extended (Phase 2+)

| Technology | Version | Role | License |
|---|---|---|---|
| Google Cloud Storage (GCS) | Managed | Backup, archive, staging | Pay-per-use |

### Data Formats

| Format | When to Use | Phase |
|---|---|---|
| Parquet | Default for all data (analytics-optimized) | 1 |
| CSV | Only when source requires it (legacy import) | 1 |
| JSON | API responses (temporary, convert to Parquet) | 1 |

### Medallion Architecture

| Zone | Storage | Description |
|---|---|---|
| Bronze | MinIO (Parquet/CSV) | Raw data, append-only, preserved as-is |
| Silver | DuckDB views/tables (Parquet output) | Cleaned, deduplicated, validated |
| Gold | PostgreSQL | Business-ready, aggregated, serving apps |

---

## 3. Transformation Layer ("The Heart")

### Core (Phase 1) — DuckDB + dbt

| Technology | Version | Role | License |
|---|---|---|---|
| DuckDB | 1.x | In-process OLAP engine, reads Parquet directly | Free |
| dbt-core | 1.8+ | SQL-based transform logic, testing, docs | Free |
| dbt-duckdb | Latest | dbt adapter for DuckDB | Free |

**Why DuckDB?**

| Advantage | Details |
|---|---|
| Zero-config | No server needed, runs in-process |
| Blazing fast | 10-100x faster than Pandas for analytical queries |
| Native Parquet | Reads Parquet without loading into memory first |
| Standard SQL | Easy to migrate to PostgreSQL/BigQuery later |
| RAM efficient | Handles data larger than RAM via disk spilling |

**dbt workflow:**

```
dbt run    → Execute models (Bronze → Silver → Gold)
dbt test   → Validate data quality
dbt docs   → Generate documentation + lineage
```

### Extended (Phase 2+)

| Technology | Version | Role | License |
|---|---|---|---|
| dbt-postgres | Latest | Transform directly on PostgreSQL | Free |
| dbt-bigquery | Latest | Transform on BigQuery (heavy analytics) | Free |
| Apache Spark (PySpark) | 3.5+ | Distributed processing (data > few GB) | Free (OSS) |
| Google Dataproc | Managed | Managed Spark cluster | Pay-per-use |
| Great Expectations | 0.18+ | Advanced data validation | Free |

### When to Use What

| Scenario | Tool | Phase |
|---|---|---|
| Transform < 2GB (most cases) | DuckDB + dbt-duckdb | 1 |
| Data quality checks | dbt tests (built-in) | 1 |
| Transform needing realtime serving | dbt-postgres | 2 |
| Data > 5GB or complex joins | PySpark (Dataproc) | 2+ |
| Advanced validation rules | Great Expectations | 2+ |

---

## 4. Serving & Vector Layer

### Lean Target (Start In Phase 3/5)

| Technology | Version | Role | Start Phase | License |
|---|---|---|---|---|
| PostgreSQL | 16.x | Gold data store, app queries, API serving | 3 | Free |
| pgvector | 0.7+ | Vector embeddings for RAG/semantic search | 5 for active use | Free |

### Extended (Phase 2+)

| Technology | Version | Role | License |
|---|---|---|---|
| Google BigQuery | Managed | Heavy analytics, BI queries | Pay-per-use |
| Redis | 7.x | Cache, session store, Celery broker when scaling | Free |

---

## 5. Orchestration Layer

### Lean Target (Start In Phase 4)

| Technology | Version | Role | Start Phase | License |
|---|---|---|---|---|
| Apache Airflow | 3.0 | DAG scheduling, dependency management | 4 | Free |
| LocalExecutor | — | Single-node execution for Lean operationalization | 4 | — |

> **Note:** Airflow 3.0 is the target version. Verify stable release availability before Phase 4. If not yet stable, fallback to Airflow 2.10.x — the DAG and provider APIs are compatible.

### Extended (Phase 2+)

| Technology | Version | Role | License |
|---|---|---|---|
| CeleryExecutor + Redis | — | Distributed task execution | Free |
| Prometheus | Latest | Metrics collection | Free |
| Grafana | Latest | Monitoring dashboards | Free |
| cAdvisor | Latest | Container resource monitoring | Free |

### Airflow Providers

| Provider | Purpose | Start Phase |
|---|---|---|
| apache-airflow-providers-postgres | PostgreSQL connection | 4 |
| apache-airflow-providers-http | REST API calls | 4 |
| airflow-dbt-python | Trigger dbt runs | 4 |
| apache-airflow-providers-google | BigQuery, GCS operators | 2 |

---

## 6. Intelligence Layer

### Lean Target (Start In Phase 5) — Graph-Augmented RAG

| Technology | Version | Role | Start Phase | License |
|---|---|---|---|---|
| FastAPI | 0.111+ | Backend framework, Dual-channel WebSocket streaming | 5 | Free |
| Neo4j | 5.x | Graph DB for Data Lineage Traversal (Context Expansion) | 5 | Free (Community) |
| PostgreSQL 16 | 16.x | Chat history, session management, vector store (pgvector) | 3 | Free |
| pgvector | 0.7+ | Vector store for semantic similarity | 5 | Free |
| Elasticsearch | 8.x | Lexical search for exact metadata matching | 5 | Free |
| Redis | 7.x | Celery broker, rate limiting, session cache | 5 | Free |
| Celery | 5.x | Background tasks (chat titles, follow-up suggestions) | 5 | Free |
| Google Gemini 2.0 Flash | API | Primary LLM (fast, cheap) | 5 | Per token |

### Extended (Phase 2+) — Agentic AI + ML

| Technology | Version | Role | License |
|---|---|---|---|
| LangGraph | Latest | Agentic AI (future), multi-step planning | Free |
| LlamaIndex | Latest | Advanced RAG patterns | Free |
| scikit-learn | 1.4+ | ML models | Free |
| XGBoost | 2.0+ | Forecasting (primary) | Free |
| Prophet | 1.1+ | Time series baseline | Free |
| statsmodels | 0.14+ | Econometric models (ARIMA, VAR) | Free |
| MLflow | 2.x | Experiment tracking, model registry | Free |
| Evidently AI | 0.4+ | Drift detection | Free |
| SHAP | 0.45+ | Model explainability | Free |

### LLM Router Strategy

| Model | Use Case | Cost |
|---|---|---|
| Gemini 2.0 Flash | Fast Q&A, summarization, routing | Low |
| Gemini 2.5 Pro | Complex reasoning, multi-step analysis | Medium |

---

## 7. Presentation Layer

### Lean Target (Start In Phase 5)

| Technology | Version | Role | Start Phase | License |
|---|---|---|---|---|
| FastAPI | 0.111+ | REST APIs for data & AI | 5 | Free |
| Uvicorn | 0.29+ | ASGI server | 5 | Free |
| Jupyter Lab | 4.x | Ad-hoc analysis, prototyping | 2 or 3 when useful | Free |

### Extended (Phase 2+)

| Technology | Version | Role | License |
|---|---|---|---|
| Google Looker Studio | Managed | BI dashboards (external stakeholders) | Free |

---

## 8. Infrastructure Layer

### Core (Phase 1)

| Technology | Version | Role | License |
|---|---|---|---|
| Docker | 24.x+ | Container runtime | Free |
| Docker Compose | 2.x+ | Multi-container orchestration | Free |
| Ubuntu Server | 22.04 LTS | OS | Free |

### Extended (Phase 2+)

| Technology | Version | Role | License |
|---|---|---|---|
| Nginx | 1.25+ | Reverse proxy, SSL termination | Free |
| Let's Encrypt (Certbot) | Latest | SSL certificates | Free |
| Cloudflare Tunnel / Tailscale | Latest | Zero-trust access | Free tier |
| Prometheus + Grafana | Latest | Monitoring & alerting | Free |

---

## 9. Governance & Security

| Technology | Role | Phase |
|---|---|---|
| PostgreSQL RBAC | Access control | 1 |
| Docker Secrets / .env | Credentials management | 1 |
| dbt tests | Data quality gates | 1 |
| Git (GitHub/GitLab) | Version control | 1 |
| Google Cloud IAM | Cloud access control | 2 |
| Google Secret Manager | API keys management | 2 |
| Evidently AI | Drift monitoring | 2 |
| SHAP + Fairlearn | AI ethics | 2 |

---

## 10. DevOps & CI/CD

| Technology | Role | Phase |
|---|---|---|
| Git (GitHub/GitLab) | Version control | 1 |
| Pre-commit hooks (ruff, black) | Code quality | 1 |
| GitHub Actions / GitLab CI | CI/CD pipelines | 2 |
| Docker Hub / GCR | Container registry | 2 |

---

## 11. Cost Summary

### Phase 1 (Lean)

| Category | Tool Count | Cost |
|---|---|---|
| On-Premise (OSS) | ~15 tools | **$0** |
| On-Premise (power + internet) | — | **~$40/month** |
| AI APIs | Google Gemini | **~$20-50/month** |
| **Total Phase 1** | | **~$60-90/month** |

### Phase 2+ (Expanded)

| Category | Tool Count | Cost |
|---|---|---|
| On-Premise (OSS) | ~30+ tools | **$0** |
| On-Premise (power + internet) | — | **~$40/month** |
| Google Cloud | 3-5 services | **~$50-140/month** |
| AI APIs | Google Gemini | **~$30-100/month** |
| **Total Phase 2+** | | **~$120-280/month** |

> Lean stack reduces initial cost to near $0 (only AI APIs), allowing concept validation before further investment.
