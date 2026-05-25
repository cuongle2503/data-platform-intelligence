# Environment Configuration — Intelligent Data Platform (IDP)

> **Status: Design / Blueprint**. Defines the target Docker Compose stack, environment variables, port mappings, resource limits, and networking for the on-premise server.
> Scope: Lean delivery with **incremental service activation** on a 16GB server. All referenced files (compose, scripts, etc.) are planned, not yet implemented.

---

## 1. Server Specifications

| Spec | Value |
|---|---|
| OS | Ubuntu Server 22.04 LTS |
| RAM | 16 GB |
| Disk | 512 GB SSD |
| Swap | 4 GB |
| CPU | To be confirmed (assume 4-8 cores) |
| Network | Static IP or DDNS, SSH access |

---

## 2. Service Activation Matrix

| Service | Image | Purpose | Start In | Required Now |
|---|---|---|---|---|
| MinIO | `minio/minio:latest` | S3-compatible object storage (Bronze/Silver) | Bootstrap | Yes |
| Neo4j 5.x | `neo4j:5-community` | Graph DB for Data Lineage | Serving / AI | No |\n| PostgreSQL 16 | `postgres:16-alpine` | Gold layer + pgvector + Airflow metadata | Transform MVP / Orchestration | Optional at bootstrap |
| Airflow Web UI/API | `apache/airflow:3.0-python3.11` | DAG UI + API server | Orchestration | No |
| Airflow Scheduler | `apache/airflow:3.0-python3.11` | DAG scheduling + execution (LocalExecutor) | Orchestration | No |
| Nginx | `nginx:1.25-alpine` | Reverse proxy, SSL termination | Hardening / external access | No |
| Redis | `redis:7-alpine` | Cache, broker for Celery-style scaling | Hardening / scale | No |

### Recommended Startup Sets

| Stage | Start These Services | Keep Off |
|---|---|---|
| Bootstrap | MinIO | Airflow, Redis, Nginx |
| Transform MVP | MinIO, PostgreSQL | Airflow, Redis, Nginx |
| Orchestration | MinIO, PostgreSQL, Airflow | Redis unless moving to Celery |
| Serving / AI | MinIO, PostgreSQL, Airflow, FastAPI, Neo4j | Redis unless cache is needed |
| Hardening / Scale | Add Nginx, Redis, monitoring | — |

Bootstrap runtime files in this repo:
- Compose file: `docker-compose.yml`
- Bucket init script: `infra/scripts/minio-init.sh`
- Runtime env file: `.env` (local only, not tracked)
- Startup command: `docker compose --env-file .env -f docker-compose.yml up -d`
- Shutdown command: `docker compose --env-file .env -f docker-compose.yml down`

### Not in Lean Bootstrap

| Service | When to Add |
|---|---|
| Airflow Worker (Celery) | When DAGs need distributed execution |
| Prometheus + Grafana | When observability is needed |
| FastAPI | Serving & Intelligence stage |

---

## 3. Port Mapping

| Service | Container Port | Host Port | Notes |
|---|---|---|---|
| Nginx | 80, 443 | 80, 443 | Only when edge profile is enabled |
| Airflow Web UI/API | 8080 | 8080 (localhost only) | Can sit behind Nginx later |
| MinIO API | 9000 | 9000 (localhost/VPN only) | Direct during bootstrap, proxy later if needed |
| Neo4j | 7474, 7687 | 7474, 7687 | Graph DB browser and bolt protocol |\n| PostgreSQL | 5432 | 5432 | Exposed for local dev tools (restrict in prod) |
| Redis | 6379 | — | Internal only |

> Do not assume Nginx from day 1. During bootstrap, bind admin ports to localhost or private network only. Add Nginx only when a stable edge entry point is required.

---

## 4. Docker Networks

| Network | Purpose | Services |
|---|---|---|
| `idp-edge` | Optional edge routing (Phase 6+) | Nginx, Airflow Webserver, MinIO, FastAPI |
| `idp-backend` | Internal service communication | Enabled backend services only (MinIO, PostgreSQL, Airflow, Redis, FastAPI) |

---

## 5. Docker Volumes

| Volume | Mount Path (container) | Purpose |
|---|---|---|
| `pg_data` | `/var/lib/postgresql/data` | PostgreSQL persistent data |
| `minio_data` | `/data` | MinIO object storage |
| `redis_data` | `/data` | Redis persistence (AOF, only when Redis enabled) |
| `airflow_logs` | `/opt/airflow/logs` | Airflow task logs |
| `airflow_dags` | `/opt/airflow/dags` | DAG files (bind mount from repo) |
| `nginx_conf` | `/etc/nginx/conf.d` | Nginx config (only when edge profile is enabled) |

---

## 6. Resource Limits (Docker)

### Bootstrap / Transform MVP

| Service | Memory Limit | Memory Reservation | CPU Limit | Notes |
|---|---|---|---|---|
| MinIO | 2 GB | 1 GB | 1 core | Object storage |
| PostgreSQL | 4 GB | 2 GB | 2 cores | Enable when Gold export or Airflow metadata is needed |
| **Baseline Reserved** | **~6.0 GB** | **~3.0 GB** | | Leaves headroom for OS + DuckDB/dbt |

### Optional Add-ons

| Service | Memory Limit | Memory Reservation | CPU Limit | Notes |
|---|---|---|---|---|
| Neo4j | 2 GB | 1 GB | 1 core | Enable for Graph-Augmented RAG |\n| Airflow Webserver | 1.5 GB | 1 GB | 1 core | UI only |
| Airflow Scheduler | 3 GB | 2 GB | 2 cores | Runs tasks (LocalExecutor) |
| Redis | 512 MB | 256 MB | 0.5 core | Only when cache/Celery is required |
| Nginx | 256 MB | 128 MB | 0.25 core | Proxy only |
| **Full Lean Stack Reserved** | **~11.3 GB** | **~6.4 GB** | | Avoid booting this full set before it is useful |

> DuckDB runs in-process. Without Airflow, it consumes host resources directly from the shell/dbt process. With Airflow enabled, DuckDB/dbt shares the Scheduler task allocation.

---

## 7. Environment Variables

### 7.1 PostgreSQL

| Variable | Example Value | Description |
|---|---|---|
| `POSTGRES_USER` | `idp_admin` | Superuser for initial setup |
| `POSTGRES_PASSWORD` | `<generated>` | Superuser password |
| `POSTGRES_DB` | `idp_warehouse` | Default database (Gold layer) |
| `POSTGRES_PORT` | `5432` | Container port |

Additional databases created via init script:
- `airflow_db` — Airflow metadata
- `idp_warehouse` — Gold layer tables + pgvector

### 7.2 MinIO

| Variable | Example Value | Description |
|---|---|---|
| `MINIO_ROOT_USER` | `minio_admin` | Admin username |
| `MINIO_ROOT_PASSWORD` | `<generated>` | Admin password |
| `MINIO_ENDPOINT` | `http://minio:9000` | Internal endpoint |

Bootstrap access paths:
- MinIO API from host: `http://127.0.0.1:9000`
- MinIO API from containers on `idp-backend`: `http://minio:9000`
- Optional host-side connector override: `MINIO_CONNECTOR_ENDPOINT=http://127.0.0.1:9000`

Buckets created on first boot:
- `bronze` — Raw ingested data (Parquet/CSV) from connectors
- `silver` — Reserved for future materialized Silver-layer Parquet (currently Silver is DuckDB views)
- `artifacts` — Reserved for dbt artifacts, logs, misc (not yet used)

### 7.3 Redis (Optional, Scale Stage)

| Variable | Example Value | Description |
|---|---|---|
| `REDIS_HOST` | `redis` | Service hostname |
| `REDIS_PORT` | `6379` | Default port |
| `REDIS_PASSWORD` | `<generated>` | Auth password |

### 7.4 Airflow

| Variable | Example Value | Description |
|---|---|---|
| `AIRFLOW__CORE__EXECUTOR` | `LocalExecutor` | Single-node execution |
| `AIRFLOW__DATABASE__SQL_ALCHEMY_CONN` | `postgresql+psycopg2://airflow:pass@postgres:5432/airflow_db` | Metadata DB |
| `AIRFLOW__CORE__DAGS_FOLDER` | `/opt/airflow/dags` | DAG directory |
| `AIRFLOW__CORE__LOAD_EXAMPLES` | `false` | No example DAGs |
| `AIRFLOW__WEBSERVER__BASE_URL` | `http://localhost:8080` | Direct access by default; change if placed behind Nginx |
| `AIRFLOW__WEBSERVER__SECRET_KEY` | `<generated>` | Session encryption |
| `AIRFLOW__LOGGING__BASE_LOG_FOLDER` | `/opt/airflow/logs` | Log storage |
| `AIRFLOW__CORE__DEFAULT_TIMEZONE` | `Asia/Ho_Chi_Minh` | Vietnam timezone |

### 7.5 Airflow Connections (configured via CLI or env)

| Connection ID | Type | Target | Used By |
|---|---|---|---|
| `postgres_warehouse` | PostgreSQL | `idp_warehouse` DB | dbt export, API queries |
| `minio_s3` | AWS (S3-compatible) | MinIO endpoint | Ingestion scripts, DuckDB reads |
| `http_world_bank` | HTTP | `https://api.worldbank.org/v2` | World Bank DAG |

### 7.6 AI APIs (Serving / AI Stage)

| Variable | Description |
|---|---|
| `GEMINI_API_KEY` | Google Gemini API key |
| `FRED_API_KEY` | FRED API key (free tier, Expand phase) |
| `NSO_API_KEY` | NSO API key (Expand phase) |

### 7.7 DuckDB (in-process, no server)

| Variable | Example Value | Description |
|---|---|---|
| `DUCKDB_S3_ENDPOINT` | `minio:9000` | MinIO endpoint for httpfs |
| `DUCKDB_S3_ACCESS_KEY` | `${MINIO_ROOT_USER}` | Reuse MinIO credentials |
| `DUCKDB_S3_SECRET_KEY` | `${MINIO_ROOT_PASSWORD}` | Reuse MinIO credentials |
| `DUCKDB_S3_USE_SSL` | `false` | No SSL for internal MinIO |
| `DUCKDB_S3_URL_STYLE` | `path` | Path-style S3 access |

---

## 8. `.env.example` Template

```env
# =============================================================================
# IDP Bootstrap Environment Configuration
# Copy to .env before running Docker Compose
# =============================================================================

# --- Bootstrap storage (required in Phase 1) ---
MINIO_ROOT_USER=minio_admin
MINIO_ROOT_PASSWORD=CHANGE_ME_minio_admin_secret
MINIO_ENDPOINT=http://minio:9000
# Optional host-side override for Phase 2 manual connectors
# MINIO_CONNECTOR_ENDPOINT=http://127.0.0.1:9000

# --- General ---
TZ=Asia/Ho_Chi_Minh
COMPOSE_PROJECT_NAME=idp

# --- Later phases (optional, do not enable in bootstrap-only stage) ---
# POSTGRES_USER=idp_admin
# POSTGRES_PASSWORD=CHANGE_ME_pg_secret
# POSTGRES_DB=idp_warehouse
# POSTGRES_PORT=5432
# REDIS_PASSWORD=CHANGE_ME_redis_secret
# AIRFLOW__CORE__EXECUTOR=LocalExecutor
# AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=postgresql+psycopg2://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/airflow_db
# AIRFLOW__WEBSERVER__SECRET_KEY=CHANGE_ME_airflow_webserver_key
# AIRFLOW__CORE__DEFAULT_TIMEZONE=Asia/Ho_Chi_Minh
# AIRFLOW__CORE__LOAD_EXAMPLES=false
# DUCKDB_S3_ENDPOINT=minio:9000
# DUCKDB_S3_ACCESS_KEY=${MINIO_ROOT_USER}
# DUCKDB_S3_SECRET_KEY=${MINIO_ROOT_PASSWORD}
# DUCKDB_S3_USE_SSL=false
# DUCKDB_S3_URL_STYLE=path
# GEMINI_API_KEY=
# FRED_API_KEY=          # Expand phase (https://fred.stlouisfed.org/docs/api/api_key.html)
# NSO_API_KEY=           # Expand phase (apply via GSO portal)
```

Bootstrap expectation:
- Create `.env` from `.env.example`
- Replace `MINIO_ROOT_PASSWORD` with a generated secret before first startup
- Keep `.env` out of version control

## 8.1 Bootstrap Storage Workflow

Start:
- `docker compose --env-file .env -f docker-compose.yml config`
- `docker compose --env-file .env -f docker-compose.yml up -d`
- `docker compose --env-file .env -f docker-compose.yml ps`

Stop:
- `docker compose --env-file .env -f docker-compose.yml down`

Logs and health:
- `docker compose --env-file .env -f docker-compose.yml logs -f minio`
- `docker compose --env-file .env -f docker-compose.yml logs minio-init`
- `curl -fsS http://127.0.0.1:9000/minio/health/live`

Persistence:
- MinIO object data lives in Docker volume `idp_minio_data`
- MinIO runtime logs are available through `docker compose logs`; no separate repo log file is created in bootstrap stage

Bootstrap smoke path convention:
- Use `bronze/manual-smoke/ingest_date=YYYY-MM-DD/<filename>` for manual Phase 1 checks
- Phase 2 ingestion scripts should move to source-oriented prefixes under `bronze/{source}/...`

First checks when MinIO is unhealthy:
- Confirm `.env` contains `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`, and `MINIO_ENDPOINT=http://minio:9000`
- Run `docker compose --env-file .env -f docker-compose.yml ps`
- Inspect `docker compose --env-file .env -f docker-compose.yml logs minio`
- Inspect `docker compose --env-file .env -f docker-compose.yml logs minio-init`
- Rerun the one-shot init flow with `docker compose --env-file .env -f docker-compose.yml up minio-init`

Host-side ingestion note:
- Phase 2 manual connectors run on the host and should upload via `http://127.0.0.1:9000`
- Keep `MINIO_ENDPOINT=http://minio:9000` for container-to-container access
- Set `MINIO_CONNECTOR_ENDPOINT=http://127.0.0.1:9000` when you want an explicit host runtime value

---

## 9. PostgreSQL Initialization

Init script runs on first container start (`/docker-entrypoint-initdb.d/`):

```sql
-- Create Airflow database
CREATE DATABASE airflow_db;
CREATE USER airflow WITH PASSWORD 'airflow_pass';
GRANT ALL PRIVILEGES ON DATABASE airflow_db TO airflow;

-- Enable pgvector on warehouse
\c idp_warehouse;
CREATE EXTENSION IF NOT EXISTS vector;

-- Create schemas for medallion layers
CREATE SCHEMA IF NOT EXISTS gold;
CREATE SCHEMA IF NOT EXISTS embeddings;

-- Service roles
CREATE ROLE readonly_role;
GRANT USAGE ON SCHEMA gold TO readonly_role;
GRANT SELECT ON ALL TABLES IN SCHEMA gold TO readonly_role;

CREATE ROLE api_service WITH LOGIN PASSWORD 'api_service_pass';
GRANT readonly_role TO api_service;
```

---

## 10. MinIO Bucket Initialization

Script runs after MinIO starts (via `mc` client):

```bash
#!/bin/bash
# Wait for MinIO to be ready
until mc alias set local http://minio:9000 ${MINIO_ROOT_USER} ${MINIO_ROOT_PASSWORD}; do
  sleep 2
done

# Create buckets
mc mb local/bronze --ignore-existing
mc mb local/silver --ignore-existing
mc mb local/artifacts --ignore-existing

# Set lifecycle: delete bronze files older than 90 days (optional)
# mc ilm rule add local/bronze --expire-days 90
```

---

## 11. Nginx Configuration (Optional Edge Profile)

```nginx
upstream airflow {
    server airflow-webserver:8080;
}

upstream minio_api {
    server minio:9000;
}

upstream minio_console {
    server minio:9001;
}

server {
    listen 80;
    server_name _;

    # Airflow UI
    location /airflow/ {
        proxy_pass http://airflow/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    # MinIO API (S3)
    location /minio/ {
        proxy_pass http://minio_api/;
        proxy_set_header Host $host;
        client_max_body_size 100M;
    }

    # MinIO Console (Web UI)
    location /minio-console/ {
        proxy_pass http://minio_console/;
        proxy_set_header Host $host;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # Health check
    location /health {
        return 200 'OK';
        add_header Content-Type text/plain;
    }
}
```

---

## 12. Docker Compose Structure

Prefer **single unified compose file** or **profiles** instead of multiple stacks.

Recommended profiles (all in `docker-compose.yml`):

- `profile: ["transform"]` → `postgres`
- `profile: ["orchestration"]` → `airflow`
- `profile: ["edge"]` → `nginx`
- `profile: ["scale"]` → `redis`, monitoring

```yaml
# docker-compose.yml (simplified overview)
version: "3.8"

services:
  postgres:
    image: pgvector/pgvector:pg16
    profiles: ["transform", "orchestration", "serve"]
    # ...resource limits, volumes, env

  minio:
    image: minio/minio:latest
    profiles: ["bootstrap", "transform", "orchestration", "serve"]
    # ...resource limits, volumes, env

  redis:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD}
    profiles: ["scale"]
    # ...resource limits, volumes

  airflow-webserver:
    image: apache/airflow:3.0-python3.11
    command: webserver
    profiles: ["orchestration", "serve"]
    depends_on: [postgres]
    # ...resource limits, volumes, env

  airflow-scheduler:
    image: apache/airflow:3.0-python3.11
    command: scheduler
    profiles: ["orchestration", "serve"]
    depends_on: [postgres, minio]
    # ...resource limits, volumes, env
    # Note: dbt + DuckDB run inside scheduler tasks

  nginx:
    image: nginx:1.25-alpine
    profiles: ["edge"]
    ports: ["80:80", "443:443"]
    depends_on: [airflow-webserver, minio]
    # ...volumes for config

  minio-init:
    image: minio/mc:latest
    profiles: ["bootstrap", "transform", "orchestration", "serve"]
    depends_on: [minio]
    entrypoint: /bin/sh /scripts/init-minio.sh
    # One-shot container to create buckets

networks:
  idp-edge:
  idp-backend:

volumes:
  pg_data:
  minio_data:
  redis_data:
  airflow_logs:
```

---

## 13. Airflow Custom Image (Dockerfile)

The base Airflow image needs additional Python packages for dbt + DuckDB + connectors:

```dockerfile
FROM apache/airflow:3.0-python3.11

USER airflow

RUN pip install --no-cache-dir \
    dbt-core==1.8.* \
    dbt-duckdb==1.8.* \
    duckdb==1.* \
    wbgapi \
    pandas \
    pyarrow \
    boto3 \
    minio \
    httpx
```

Build and reference in docker-compose:
```yaml
airflow-scheduler:
  build:
    context: ../docker/airflow
    dockerfile: Dockerfile
```

---

## 14. Startup Order & Health Checks

```
Bootstrap
1. minio        (healthcheck: curl http://localhost:9000/minio/health/live)
2. minio-init   (one-shot: create buckets, then exit)

Transform MVP
3. postgres     (healthcheck: pg_isready)

Orchestration
4. airflow-scheduler (depends: postgres, minio)
5. airflow-webserver (depends: postgres)

Hardening / Scale
6. nginx        (depends: airflow-webserver, minio)
7. redis        (healthcheck: redis-cli ping)
```

---

## 15. Security Checklist (Phase 1)

| Item | Status | Notes |
|---|---|---|
| All passwords in `.env`, not in compose file | Required | `.env` in `.gitignore` |
| PostgreSQL not exposed to internet | Required | Only localhost:5432 for dev tools |
| MinIO not exposed directly to the internet | Required | Bind to localhost/VPN or put behind Nginx later |
| Airflow admin password changed from default | Required | Set on first `airflow users create` |
| Redis password set | Required when Redis is enabled | `--requirepass` flag |
| UFW firewall: open only the ports currently in use | Required | Avoid opening 80/443 before Nginx exists |
| SSH key-only auth (no password) | Recommended | |
| Fail2ban installed | Recommended | Brute-force protection |

---

## 16. Backup Strategy (Phase 1 — Local)

| What | Method | Frequency | Retention |
|---|---|---|---|
| PostgreSQL (Gold + Airflow) | `pg_dump` → local file | Daily | 7 days |
| MinIO (Bronze/Silver) | Already on disk; rsync to external | Weekly | 30 days |
| Airflow DAGs + config | Git repo | On every push | Unlimited |
| `.env` secrets | Encrypted copy off-server | On change | Latest only |

Phase 2 adds GCS backup for disaster recovery.
