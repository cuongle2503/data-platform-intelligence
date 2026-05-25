# Manual Ingestion Runbook — Intelligent Data Platform (IDP)

> **Status: ✅ Verified 2026-05-20**. Manual-first connector execution workflow.
> All commands below have been smoke-tested against the live stack.

---

## 1. Shared Requirements

- Python runtime: `python3` (validated with Python 3.10+)
- Install dependencies:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
```

- Required env vars (loaded from `.env` via Pydantic BaseSettings):
  - `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`
  - `MINIO_CONNECTOR_ENDPOINT=http://127.0.0.1:9000` (for host-side execution)

Notes:
- Connectors run on the host, not inside Docker.
- All config is centralized in `idp/core/config.py` — reads from `.env` automatically.
- If your shell proxy blocks a source, add `--ignore-proxy`.

---

## 2. World Bank Open Data

Using entry point:

```bash
ingest-world-bank --start-year 2023 --end-year 2024
```

Or as module:

```bash
python3 -m idp.ingestion.connectors.world_bank.connector --start-year 2023 --end-year 2024
```

Expected output:
- Local Parquet files in `tmp/world_bank/year=<YYYY>/data.parquet`
- MinIO objects in `s3://bronze/world_bank/indicators/year=<YYYY>/data.parquet`
- Schema: all numeric columns are explicit `int64`/`float64` (no type inference drift)

First checks on failure:
- Re-run with `--ignore-proxy` if corporate proxy interferes
- Confirm `docker compose --env-file .env ps`
- Confirm `curl -fsS http://127.0.0.1:9000/minio/health/live`

---

## 3. World Bank Documents & Reports (WDS)

Metadata-only (default):

```bash
ingest-world-bank-docs
```

With full text extraction (server-side text fetch + chunking):

```bash
ingest-world-bank-docs --full-text
```

Or as module:

```bash
python3 -m idp.ingestion.connectors.world_bank_docs.connector
python3 -m idp.ingestion.connectors.world_bank_docs.connector --full-text
```

Expected output:
- Local Parquet: `tmp/world_bank_docs/metadata/documents.parquet`
- With `--full-text`: `tmp/world_bank_docs/chunks/chunks.parquet`
- MinIO objects:
  - `s3://bronze/world_bank_docs/metadata/documents.parquet`
  - `s3://bronze/world_bank_docs/chunks/chunks.parquet`

---


## 4. Validation Order

Recommended manual validation order:

```bash
# Start full stack
docker compose --env-file .env up -d

# Run connectors (host-side)
ingest-world-bank --start-year 2024 --end-year 2024
ingest-world-bank-docs

# Verify data in MinIO
docker exec idp-minio-1 mc ls --recursive local/bronze/

# Tear down
docker compose --env-file .env down
```

---

## 5. Rerun And Idempotency

- World Bank: reruns overwrite the same `year=<YYYY>/data.parquet` partition
- World Bank Docs: reruns overwrite `metadata/documents.parquet` and `chunks/chunks.parquet`

---

## 6. E2E Pipeline Test (Full Walkthrough)

Tự tay chạy pipeline từ đầu đến cuối để xác minh toàn bộ data flow.

### 6.1 Prerequisites

```bash
cd /home/pc/my-projects/data-platform-intelligent/backend
python3 -m venv .venv && . .venv/bin/activate && pip install -e .
```

### 6.2 Start Infrastructure

```bash
docker compose --env-file .env up -d
```

Đợi ~15s cho tất cả services healthy:

```bash
docker ps --format "table {{.Names}}\t{{.Status}}"
# Cần thấy: idp-minio-1 (healthy), idp-postgres-1 (healthy), idp-airflow-1 (Up)
```

### 6.3 Check Phase 1 — Bootstrap

```bash
# MinIO buckets
docker exec idp-minio-1 mc ls local/
# Cần thấy: artifacts/, bronze/, silver/
# Note: chỉ bronze/ có data (ingestion output). silver/ và artifacts/ là bucket dự phòng.

# PostgreSQL databases
PGPASSWORD=admin123 psql -h localhost -p 5433 -U admin -c "\l"
# Cần thấy: idp_warehouse, airflow_db
```

### 6.4 Check Phase 2 — Ingestion (data đã có sẵn)

```bash
# Indicators trong MinIO
docker exec idp-minio-1 mc ls --recursive local/bronze/world_bank/indicators/
# 11 partitions year=2015 → year=2025

# Docs trong MinIO
docker exec idp-minio-1 mc ls --recursive local/bronze/world_bank_docs/
# metadata/documents.parquet + chunks/chunks.parquet

# Sample data bằng DuckDB
duckdb -c "
SELECT count(*) AS rows, min(year) AS from, max(year) AS to
FROM read_parquet('tmp/world_bank/*/data.parquet', hive_partitioning=true);"
```

### 6.5 Check Phase 3 — Transformation (dbt models)

```bash
# Xem tất cả model trong DuckDB
duckdb tmp/duckdb/idp.db -c "
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'main_gold' ORDER BY table_name;"

# Row counts
duckdb tmp/duckdb/idp.db -c "
SELECT 'dim_countries' AS model, count(*) AS rows FROM main_gold.dim_countries
UNION ALL SELECT 'dim_indicators', count(*) FROM main_gold.dim_indicators
UNION ALL SELECT 'dim_dates', count(*) FROM main_gold.dim_dates
UNION ALL SELECT 'fact_economic_indicators', count(*) FROM main_gold.fact_economic_indicators;"

# Query mẫu: GDP của Vietnam các năm
duckdb tmp/duckdb/idp.db -c "
SELECT dd.full_date, f.value
FROM main_gold.fact_economic_indicators f
JOIN main_gold.dim_countries dc ON f.country_key = dc.country_key
JOIN main_gold.dim_indicators di ON f.indicator_key = di.indicator_key
JOIN main_gold.dim_dates dd ON f.date_key = dd.date_key
WHERE dc.country_name = 'Vietnam' AND di.indicator_name = 'GDP (current USD)'
ORDER BY dd.full_date;"
```

### 6.6 Check Phase 3b — Gold Export (DuckDB → PostgreSQL)

```bash
# Row counts trong PostgreSQL
PGPASSWORD=idp_pg_secret_2026 psql -h localhost -p 5433 -U idp_admin -d idp_warehouse -c "
SELECT 'dim_countries' AS tbl, count(*) FROM gold.dim_countries
UNION ALL SELECT 'dim_indicators', count(*) FROM gold.dim_indicators
UNION ALL SELECT 'dim_dates', count(*) FROM gold.dim_dates
UNION ALL SELECT 'fact_economic_indicators', count(*) FROM gold.fact_economic_indicators;"

# So sánh DuckDB vs PostgreSQL (phải khớp)
duckdb tmp/duckdb/idp.db -c "
SELECT 'gold' AS layer, 'fact' AS tbl, count(*) AS rows FROM main_gold.fact_economic_indicators;"
```

### 6.7 Check Phase 4 — Airflow DAGs

```bash
# Xem danh sách DAGs (cần Airflow admin password)
# Mở browser: http://localhost:8080
# Login: admin / <password trong .env: AIRFLOW_WEBSERVER_SECRET_KEY>

# Kiểm tra DAG status qua DB
docker exec -i idp-postgres-1 psql -U idp_admin -d airflow_db -c "
SELECT dag_id, is_paused FROM dag ORDER BY dag_id;"

# Kiểm tra recent runs
docker exec -i idp-postgres-1 psql -U idp_admin -d airflow_db -c "
SELECT dag_id, state, start_date
FROM dag_run
WHERE start_date IS NOT NULL
ORDER BY start_date DESC LIMIT 10;"
```

### 6.8 Trigger Full Pipeline bằng tay

Nếu muốn chạy lại toàn bộ pipeline từ Airflow UI:

1. Mở **http://localhost:8080** → login
2. Trigger theo thứ tự:
   - **ingest_world_bank** → đợi success
   - **run_dbt_transform** → tự trigger sau ingest → đợi success
   - **export_gold_to_postgres** → tự trigger sau transform → đợi success
3. Chạy độc lập: **ingest_world_bank_docs** (không phụ thuộc DAG khác)

### 6.9 Teardown

```bash
docker compose --env-file .env down
# Giữ lại data volumes: bỏ -v flag
```

### 6.10 Known Issues (đã gặp khi test)

| Vấn đề | Nguyên nhân | Cách fix |
|---|---|---|
| `ingest_world_bank` DAG failed lần đầu | MinIO chưa ready khi Airflow trigger ngay sau boot — task `check_minio_health` bị `up_for_retry` | Đợi MinIO healthy rồi trigger lại, hoặc để Airflow auto-retry |
| PyArrow `read_table` lỗi schema merge trên host | PyArrow dataset API infer partition field `year` thành `int32` thay vì `int64` | Dùng `pq.ParquetFile(path)` đọc từng file, hoặc chỉ định explicit partition schema: `ds.partitioning(pa.schema([('year', pa.int64())]), flavor='hive')` |
