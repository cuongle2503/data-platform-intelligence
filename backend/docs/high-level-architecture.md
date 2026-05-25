# High-Level Architecture — Intelligent Data Platform (IDP)

> **Status: Design / Blueprint**. Target architecture — implementation pending.
> Strategy: "Basic first, modern later" — Lean Data Stack
> Hybrid Deployment: On-Premise Server (16GB RAM / 512GB SSD) + Google Cloud Platform (expand later)
> Version: 3.0 — Lean-first approach, maximize open-source

---

## 1. Design Philosophy

| Principle | Explanation |
|---|---|
| Basic first, modern later | Get end-to-end working first, optimize later |
| Lean stack | Fewest tools possible, each must justify its value |
| Open-source first | No vendor lock-in, no license fees |
| Single-node first | Max out 16GB/512GB before scaling to cloud |
| DuckDB + dbt = the heart | Fast local processing, SQL-based, testable |

---

## Runtime Activation Rule

- The 5-layer model is the **target architecture**, not an instruction to boot every service on day 1.
- In Lean delivery, enable services only when they unlock the next concrete capability.
- Prefer this activation order on a 16GB server:

| Stage | Capability unlocked | Services to start |
|---|---|---|
| Bootstrap | Raw storage + manual experimentation | MinIO |
| Transform MVP | Bronze → Silver → Gold pipeline | MinIO + DuckDB/dbt (in-process), PostgreSQL only when Gold export starts |
| Orchestrate | Scheduled and retryable jobs | Airflow + PostgreSQL metadata DB |
| Serve | API and RAG endpoints | FastAPI + pgvector |
| Harden / Scale | Edge routing, cache, monitoring | Nginx, Redis, Prometheus/Grafana |

**Rule of thumb:** if a service does not reduce manual work or enable the current phase's deliverable, keep it off.

---

## 2. Five-Layer Model (The "Lean" Data Stack)

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                                                                                  │
│   Layer 5: ORCHESTRATION                                                         │
│   ┌──────────────────────────────────────────────────────────────────────────┐   │
│   │                     Apache Airflow 3.0                                   │   │
│   │   Scheduling │ Dependency │ Retry │ Alerting │ Monitoring                │   │
│   └──────────────────────────────────────────────────────────────────────────┘   │
│                                       │                                          │
│   Layer 4: INTELLIGENCE               │                                          │
│   ┌──────────────────────────────────────────────────────────────────────────┐   │
│   │   14-step Graph-Augmented RAG Pipeline + Google Gemini                   │   │
│   │   Neo4j (Data Lineage Graph) │ pgvector │ Dual-channel WebSocket Chatbot │   │
│   └──────────────────────────────────────────────────────────────────────────┘   │
│                                       │                                          │
│   Layer 3: SERVING & VECTOR           │                                          │
│   ┌──────────────────────────────────────────────────────────────────────────┐   │
│   │   PostgreSQL 16 + pgvector                                               │   │
│   │   Clean data (Gold) │ Embeddings │ API serving │ App queries             │   │
│   └──────────────────────────────────────────────────────────────────────────┘   │
│                                       │                                          │
│   Layer 2: TRANSFORMATION             │                                          │
│   ┌──────────────────────────────────────────────────────────────────────────┐   │
│   │   DuckDB (Engine) + dbt-core (Logic)                                     │   │
│   │   Bronze → Silver → Gold │ Data Testing │ Metrics │ Documentation        │   │
│   └──────────────────────────────────────────────────────────────────────────┘   │
│                                       │                                          │
│   Layer 1: INGESTION & RAW STORAGE    │                                          │
│   ┌──────────────────────────────────────────────────────────────────────────┐   │
│   │   Python (requests, pandas) → Parquet/CSV files (MinIO/Local)            │   │
│   │   Sources: World Bank │ NSO │ FRED │ Files                            │   │
│   └──────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. System Context

```
                        ┌──────────────────────────────────┐
                        │          STAKEHOLDERS            │
                        │  • Business Leadership           │
                        │  • Data Engineers                │
                        │  • Analysts / End Users          │
                        └───────────────┬──────────────────┘
                                        │
                                        ▼
┌───────────────────────────────────────────────────────────────────────────────────┐
│                       INTELLIGENT DATA PLATFORM (IDP)                             │
│                                                                                   │
│   ┌──────────────────────────────────────────────────────────────────────────┐    │
│   │              ON-PREMISE SERVER (16GB / 512GB SSD)                        │    │
│   │                                                                          │    │
│   │   Python Scripts → Parquet (MinIO) → DuckDB+dbt → PostgreSQL → AI/Apps   │    │
│   │                         ↕ Airflow orchestrates everything                │    │
│   └──────────────────────────────────────────────────────────────────────────┘    │
│                                                                                   │
│   ┌──────────────────────────────────────────────────────────────────────────┐    │
│   │              GOOGLE CLOUD (expand when needed)                           │    │
│   │   GCS (backup) │ BigQuery (heavy analytics) │ AI APIs │ Looker Studio    │    │
│   └──────────────────────────────────────────────────────────────────────────┘    │
│                                                                                   │
└───────────────────────────────────────────────────────────────────────────────────┘
          ▲                                                        ▲
          │                                                        │
┌─────────┴──────────┐                                ┌────────────┴────────────┐
│   INTERNAL DATA    │                                │    EXTERNAL DATA        │
│  • ERP / CRM       │                                │  • NSO (Vietnam Stats)  │
│  • Databases       │                                │  • FRED (US Fed)        │
│  • Files / Logs    │                                │  • World Bank           │
└────────────────────┘                                └─────────────────────────┘
```

---

## 4. Data Flow (Lean Path)

```
┌────────────────┐       ┌─────────────────────────────────────────────────────────┐
│  DATA SOURCES  │       │              ON-PREMISE PROCESSING                      │
│                │       │                                                         │
│  • World Bank  │       │  ┌──────────┐   ┌──────────────┐   ┌────────────────┐   │
│  • NSO (VN)    │──────►│  │  BRONZE  │──►│    SILVER    │──►│     GOLD       │   │
│  • FRED (US)   │       │  │          │   │              │   │                │   │
│                │       │  │ Parquet  │   │  DuckDB+dbt  │   │  PostgreSQL    │   │
│  • CSV/Excel   │       │  │ (MinIO)  │   │  (cleaned)   │   │  (+ pgvector)  │   │
│                │       │  └──────────┘   └──────────────┘   └───────┬────────┘   │
└────────────────┘       │                                            │            │
                         │       Airflow 3.0 orchestrates ────────────┘            │
                         └─────────────────────────────────────────────────────────┘
                                                                      │
                                                          ┌───────────┼───────────┐
                                                          ▼           ▼           ▼
                                                    ┌──────────┐ ┌────────┐ ┌─────────┐
                                                    │ FastAPI  │ │Jupyter │ │   AI    │
                                                    │ (APIs)   │ │ (Adhoc)│ │ (RAG)   │
                                                    └──────────┘ └────────┘ └─────────┘
```

---

## 5. Layer Details

### Layer 1: Ingestion (Data Collection)

| Component | Tool | Notes |
|---|---|---|
| Collection scripts | Python (requests, httpx, pandas) | API calls, scraping |
| Storage format | Parquet (preferred), CSV (fallback) | Parquet is 5-10x smaller than CSV |
| Object storage | MinIO (S3-compatible) | Raw zone, append-only |
| Scheduling | Airflow DAGs | Frequency: daily/weekly/monthly per source |

### Layer 2: Transformation ("The Heart")

| Component | Tool | Notes |
|---|---|---|
| Compute engine | DuckDB | Blazing fast Parquet processing, zero-config, in-process |
| Logic management | dbt-core + dbt-duckdb | SQL models, version control, testable |
| Data testing | dbt tests (built-in) | not_null, unique, accepted_values, custom |
| Documentation | dbt docs | Auto-generated lineage + catalog |
| Medallion | Bronze (raw) → Silver (clean) → Gold (business-ready) | |

### Layer 3: Serving & Vector

| Component | Tool | Notes |
|---|---|---|
| Operational DB | PostgreSQL 16 | Gold data for apps, APIs |
| Vector store | pgvector extension | Embeddings for RAG |
| Caching | Redis | Optional; add only when API cache or Celery-style scaling is needed |

### Layer 4: Intelligence

| Component | Tool | Notes |
|---|---|---|
| RAG Pipeline | Custom 14-step Graph-Augmented RAG | Hard-coded imperative workflow (deterministic), Neo4j integration |
| Knowledge Graph | Neo4j | Deep data lineage traversal (context expansion) |
| Chatbot Streaming | Dual-channel WebSocket | Fast token streaming with REST backup |
| Primary LLM | Google Gemini (Flash 2.0 + Pro 2.5) | Fast Q&A + complex reasoning |
| App framework | FastAPI + Jupyter | API + exploration |

### Layer 5: Orchestration

| Component | Tool | Notes |
|---|---|---|
| Scheduler | Apache Airflow 3.0 | DAG-based, Python-native |
| Executor | LocalExecutor (basic) → CeleryExecutor (scale) | |
| Monitoring | Airflow UI + Prometheus/Grafana | |
| Alerting | Telegram/Email on failure | |

---

## 6. Deployment View (Lean)

> This is the **fully activated Lean target** on a single node, not the mandatory day-1 startup set.

```
┌───────────────────────────────────────────┐       ┌─────────────────────────────────┐
│        ON-PREMISE SERVER                  │       │     GOOGLE CLOUD (Phase 2+)     │
│        16GB RAM / 512GB SSD               │       │                                 │
│                                           │       │  ┌───────────────────────────┐  │
│  ┌─────────────────────────────────────┐  │       │  │   GCS (Backup/Archive)    │  │
│  │        Docker Compose Stack         │  │       │  └───────────────────────────┘  │
│  │                                     │  │       │                                 │
│  │  ┌───────────────────────────────┐  │  │       │  ┌───────────────────────────┐  │
│  │  │  Airflow 3.0                  │  │  │       │  │   BigQuery (when needed)  │  │
│  │  │  (webserver + scheduler)      │  │  │       │  │   Heavy analytics         │  │
│  │  └───────────────────────────────┘  │  │       │  └───────────────────────────┘  │
│  │  ┌───────────────────────────────┐  │  │       │                                 │
│  │  │  PostgreSQL 16 + pgvector     │  │  │       │  ┌───────────────────────────┐  │
│  │  └───────────────────────────────┘  │  │       │  │   AI APIs                 │  │
│  │  ┌───────────────────────────────┐  │  │       │  │   • Gemini Flash (fast)      │  │
│  │  │  MinIO (object storage)       │  │  │       │  │   • Gemini Pro (complex)   │  │
│  │  └───────────────────────────────┘  │  │       │  │                              │  │
│  │  ┌───────────────────────────────┐  │  │       │  └───────────────────────────┘  │
│  │  │  Redis                        │  │  │       │                                 │
│  │  └───────────────────────────────┘  │  │       │  ┌───────────────────────────┐  │
│  │  ┌───────────────────────────────┐  │  │       │  │   Looker Studio (BI)      │  │
│  │  │  FastAPI                      │  │  │       │  └───────────────────────────┘  │
│  │  └───────────────────────────────┘  │  │       │                                 │
│  │  ┌───────────────────────────────┐  │  │       │                                 │
│  │  │  Nginx (reverse proxy)        │  │  │       │                                 │
│  │  └───────────────────────────────┘  │  │       │                                 │
│  └─────────────────────────────────────┘  │       │                                 │
│                                           │       │                                 │
│  DuckDB: runs in-process (no separate     │       │                                 │
│  container needed, dbt calls directly)    │       │                                 │
│                                           │       │                                 │
└───────────────────────────────────────────┘       └─────────────────────────────────┘
```

---

## 7. Lean Rollout vs Full Stack Comparison

| Aspect | Lean Rollout | Full (Phase 2+) |
|---|---|---|
| Ingestion | Python scripts after MinIO bootstrap | + BigQuery, GCS backup |
| Compute | DuckDB (in-process) | + Spark/Dataproc (data > 1GB) |
| Transform | dbt-duckdb | + dbt-postgres, dbt-bigquery |
| Storage | MinIO first, PostgreSQL when Gold export starts | + BigQuery, GCS |
| Serving | FastAPI only when consumers need endpoints | + Looker Studio |
| AI | Deferred until Gold data and serving path are stable | + Agentic framework, MLOps |
| Monitoring | Airflow UI only after orchestration starts | + Prometheus/Grafana |
| Data Quality | dbt tests | + Great Expectations |

---

## 8. Expansion Roadmap (Basic → Modern)

```
Phase 1 (Lean)          Phase 2 (Expand)         Phase 3 (Scale)
4-6 weeks               4-6 weeks                Ongoing
─────────────────────   ─────────────────────    ─────────────────────
• MinIO bootstrap       • NSO + FRED connectors  • Spark (heavy data)
• Python ingestion      • dbt-postgres           • BigQuery (analytics)
• DuckDB + dbt-duckdb   • Semantic Layer         • Advanced MLOps
• PostgreSQL when Gold   • Looker Studio          • Agentic AI full
• Airflow after manual  • RAG + LLM basic        • Multi-LLM router
  runs are stable       • Cloud backup (GCS)     • Real-time (Pub/Sub)
• FastAPI when serving
```

---

## 9. Key Design Decisions (Updated)

| # | Decision | Choice | Rationale |
|---|---|---|---|
| 1 | Compute engine (transform) | DuckDB | Zero-config, processes Parquet 10-100x faster than Pandas, runs on single node |
| 2 | Transform logic | dbt-core + dbt-duckdb | SQL-based, testable, documented, version controlled |
| 3 | Primary storage | PostgreSQL + pgvector | Free, reliable, supports RAG, serves apps |
| 4 | Raw storage | MinIO (Parquet files) | S3-compatible, easy to migrate to cloud later |
| 5 | Orchestration | Apache Airflow 3.0 | Python-native, industry standard |
| 6 | AI strategy | API-based (Google Gemini) | 16GB can't host LLMs locally |
| 7 | Presentation (basic) | FastAPI + Jupyter | API-first, no UI framework needed initially |
| 8 | Ingestion | Python scripts | Simple, low RAM, full control |
| 9 | Format | Parquet over CSV | 5-10x smaller, columnar, type-safe |
| 10 | Scale strategy | Vertical first → Cloud burst later | Max out on-prem before investing more |
| 11 | Service activation | Incremental by phase | Avoid running unused containers on a 16GB server |

---

## 10. Cost Estimate (Lean Phase)

| Component | Monthly | Notes |
|---|---|---|
| On-Premise (power + internet) | ~$40 | Fixed cost |
| AI APIs (Google Gemini) | ~$20-50 | Quota enforced |
| GCS Backup (Phase 2) | ~$5-10 | Archive tier |
| **Total Phase 1** | **~$60-90/month** | Minimal cloud dependency |
| **Total Phase 2+** | **~$120-280/month** | + BigQuery, Looker |

---

## 11. Risk Mitigation

| Risk | Impact | Mitigation |
|---|---|---|
| DuckDB memory limit (16GB) | Medium | Partition large datasets, process in chunks |
| Server failure | High | Daily backup to GCS (Phase 2); local backup (Phase 1) |
| Single point of failure | High | Docker restart policies; external backup |
| AI API cost spike | Low | Daily quota caps; fallback to cheaper models |
| Data quality issues | Medium | dbt tests on every run; alerting |
| Outgrowing DuckDB | Low | Migrate to dbt-postgres or Spark when data exceeds a few GB |
