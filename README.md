# 🚀 Intelligent Data Platform (IDP)

Data platform for economic indicators — ingestion, transformation, serving, and **Graph-Augmented RAG** AI querying.

> **Status: Implemented & Monitoring Active.** Fully functional medallion architecture with real-time observability.

## 🏗️ Architecture Overview

```text
Data Sources ➔ Ingestion (Python) ➔ Bronze (MinIO/Parquet) ➔ Silver (DuckDB+dbt) ➔ Gold (Postgres+pgvector) ➔ API (FastAPI) ➔ AI (Graph RAG)
                                                                                               ▲
                                                                                     Airflow Orchestrates
```

### 🛠️ The Tech Stack
| Layer | Technology | Role |
| :--- | :--- | :--- |
| **Ingestion** | Python, `wbgapi`, Pandas | World Bank API connectors |
| **Storage** | MinIO (S3-compatible) | Bronze layer (raw parquet files) |
| **Transform** | DuckDB + dbt-core | Silver layer processing |
| **Serving** | PostgreSQL 16 + `pgvector` | Gold layer (Star Schema) & Vector Store |
| **Intelligence** | Neo4j + Elasticsearch + Gemini | Graph-Augmented RAG Pipeline |
| **Orchestration** | Apache Airflow | Pipeline scheduling & dependency management |
| **Observability** | Prometheus + Grafana + cAdvisor | Full-stack metrics & container monitoring |

---

## ⚡ Quick Start

### 1. Requirements
- Docker & Docker Compose
- Python 3.10+
- Gemini API Key

### 2. Startup
```bash
# Clone and enter
git clone <repo-url>
cd data-platform-intelligent

# Setup environment
cp .env.example .env  # Add your GEMINI_API_KEY

# Launch everything
docker compose --env-file .env up -d
```

### 3. Access
- **API**: `http://localhost:8001/docs`
- **Airflow**: `http://localhost:8080` (admin/admin123)
- **Grafana**: `http://localhost:3000` (admin/admin123)
- **MinIO Console**: `http://localhost:9001`
- **Neo4j Bloom**: `http://localhost:7474`

---

## 📊 Monitoring & Observability

IDP is equipped with a comprehensive monitoring stack. Visit **Grafana** to view:
- **IDP Containers**: Real-time RAM/CPU/IO for all 10+ services via cAdvisor.
- **Airflow Stats**: DAG success rates, task latencies, and worker health.
- **Service Overviews**: Dedicated dashboards for Postgres, Redis, and Elasticsearch.

---

## 🤖 AI Intelligence (Graph RAG)

Our chatbot doesn't just search text; it understands relationships:
1. **Lexical Search**: Elasticsearch finds exact indicator codes/names.
2. **Vector Search**: `pgvector` retrieves semantic context from documents.
3. **Graph Traversal**: Neo4j explores connections between countries, indicators, and topics.
4. **Synthesis**: Google Gemini 1.5 Pro generates insights based on the combined context.

---

## 📁 Repository Structure
- `backend/idp/`: Core data engineering code (ingestion, transformation).
- `backend/services/`: API and AI RAG implementation.
- `backend/orchestration/`: Airflow DAG definitions.
- `backend/infra/`: Docker, Nginx, and Monitoring configuration.
- `backend/transform/dbt/`: dbt models and schema definitions.

---

## 🛡️ Security & Hardening
- **RBAC**: Proper database roles (`api_service`, `airflow_role`, `transform_role`).
- **Secret Management**: Environment-driven configuration via Pydantic Settings.
- **Internal Network**: All backend services communicate via isolated Docker bridge.

---
🤖 Generated & Maintained with [Claude Code](https://claude.com/code)
