# Phase 4: Operationalize with Airflow

> **Status: ✅ Done (verified 2026-05-20) | Duration: ~5-6 ngày | Rule: DAGs chỉ orchestrate, business logic nằm ở ingestion/transform**
>
> **Triển khai thực tế:** Airflow 3.0.6 `standalone` (gộp scheduler + api-server + dag-processor + triggerer trong 1 container), 5GB memory, parallelism=1. Fixed fernet key để connections tồn tại qua restart. 4 DAGs đã parse và test E2E thành công, cross-DAG triggers đã wired.

---

## Mục tiêu

Airflow 3.0 chạy trên server, 4 DAGs hoạt động: 2 ingestion + 1 transform + 1 export. Có retry, log, alerting baseline.

---

## 4.1 Airflow platform (1.5 ngày)

- [x] 4.1.1 Tạo `infra/docker/airflow/Dockerfile`
  - FROM `apache/airflow:3.0.6-python3.12`
  - USER airflow
  - RUN `pip install --no-cache-dir dbt-core dbt-duckdb duckdb wbgapi pandas pyarrow boto3 psycopg2-binary`
  - Pre-cache DuckDB extensions (`httpfs`, `postgres_scanner`) vào `/home/airflow/.duckdb/extensions/` vì Docker build không có internet

- [x] 4.1.2 Thêm Airflow service vào `docker-compose.yml`
  - service `airflow` (single-container `standalone` mode, gộp scheduler + api-server + dag-processor + triggerer):
    - build từ `infra/docker/airflow/Dockerfile`
    - command `standalone`
    - port `8080:8080`
    - depends_on postgres (healthy), minio (healthy)
    - env `AIRFLOW__CORE__EXECUTOR=LocalExecutor`, `AIRFLOW__CORE__PARALLELISM=1`
    - env `AIRFLOW__CORE__FERNET_KEY` cố định để connections tồn tại qua restart
    - env `AIRFLOW__API__SECRET_KEY` (không phải `AIRFLOW__WEBSERVER__SECRET_KEY`)
    - volume mount `./orchestration/airflow/dags:/opt/airflow/dags:ro`
    - volume mount `./idp:/opt/airflow/idp:ro`
    - volume mount `./transform:/opt/airflow/transform:rw` (dbt cần ghi target/, logs/)
    - volume mount `./tmp/duckdb:/opt/airflow/tmp/duckdb`
    - resource limit: 5GB mem, 2 CPU (3GB không đủ cho standalone + dbt tasks)

- [x] 4.1.3 Start Airflow
  - `docker compose --env-file .env up -d`
  - `airflow standalone` tự động init DB + tạo admin user

- [x] 4.1.4 Verify
  - Mở `http://<server>:8080` → login với password từ logs
  - Không có DAG errors, không có import errors

---

## 4.2 Airflow connections (0.5 ngày)

- [x] 4.2.1 Tạo connection `postgres_warehouse`
  - Conn Type: Postgres
  - Host: postgres, Port: 5432
  - Schema: idp_warehouse
  - Login: idp_admin, Password: idp_pg_secret_2026

- [x] 4.2.2 Tạo connection `minio_health` (HttpSensor cho MinIO health check)
  - Conn Type: HTTP
  - Host: `http://minio:9000`

- [x] 4.2.3 Verify connections trong Airflow UI → Admin → Connections

---

## 4.3 DAG: `ingest_world_bank` (0.5 ngày)

- [x] 4.3.1 Tạo `orchestration/airflow/dags/ingest_world_bank.py`
  - schedule: `@monthly` (ngày 1, 6:00 AM)
  - DAG args: start_date, catchup=False, retries=3, retry_delay=5min
  - Task 1: `check_minio_health` → `HttpSensor` ping MinIO health endpoint
  - Task 2: `run_ingestion` → `PythonOperator` gọi `ingestion.connectors.world_bank.main` với subprocess
  - Task 3: `verify_output` → `PythonOperator` kiểm tra object tồn tại trong MinIO bucket
  - Task 1 >> Task 2 >> Task 3
  - on_failure_callback: gửi alert (Telegram hoặc email)

- [x] 4.3.2 Test DAG
  - Trigger manual trong UI → tất cả tasks xanh
  - Verify object mới trong MinIO `bronze/world_bank/indicators/`
  - Test retry: stop MinIO → trigger → task fail → retry → start MinIO → retry thành công

---

## 4.4 DAG: `ingest_world_bank_docs` (0.5 ngày)

- [x] 4.4.1 Tạo `orchestration/airflow/dags/ingest_world_bank_docs.py`
  - schedule: `@monthly` (ngày 2, 6:00 AM)
  - Task 1: `check_minio_health`
  - Task 2: `run_metadata_ingestion` → subprocess gọi connector không `--full-text`
  - Task 3: `run_fulltext_ingestion` → subprocess gọi connector với `--full-text`
  - Task 4: `verify_metadata`, Task 5: `verify_chunks`
  - Task 1 >> Task 2 >> Task 4, Task 1 >> Task 3 >> Task 5
  - Branching: nếu tháng không phải cuối quý → skip Task 3+5

- [x] 4.4.2 Test DAG
  - Trigger manual → tasks xanh, objects trong MinIO

---

## 4.5 DAG: `run_dbt_transform` (1 ngày)

- [x] 4.5.1 Tạo `orchestration/airflow/dags/run_dbt_transform.py`
  - schedule: `None` — **trigger-based**, chỉ chạy sau khi ingestion DAG hoàn thành
  - Nhận trigger từ `ingest_world_bank`, `ingest_world_bank_docs` qua `TriggerDagRunOperator`
  - Task 1: `setup_duckdb_secret` → `PythonOperator` tạo S3 secret trong DuckDB để đọc MinIO
  - Task 2: `dbt_seed` → `BashOperator` `cd /opt/airflow/transform/dbt && dbt seed --profiles-dir .`
  - Task 3: `dbt_run` → `BashOperator` `dbt run --profiles-dir .`
  - Task 4: `dbt_test` → `BashOperator` `dbt test --profiles-dir .`
  - Task 5: `check_test_results` → `PythonOperator` parse `target/run_results.json`, fail nếu có lỗi
  - Task 6: `trigger_export` → `TriggerDagRunOperator` kích hoạt `export_gold_to_postgres`
  - Chain: setup >> seed >> run >> test >> check >> trigger_export
  - retries=1 (dbt đã có logic retry nội bộ)

- [x] 4.5.2 Test DAG
  - Trigger → dbt run + test thành công
  - Verify dbt artifacts: `target/run_results.json` có kết quả

---

## 4.6 DAG: `export_gold_to_postgres` (0.5 ngày)

- [x] 4.6.1 Tạo `orchestration/airflow/dags/export_gold_to_postgres.py`
  - Trigger: sau khi `run_dbt_transform` hoàn thành (qua `TriggerDagRunOperator`)
  - schedule: None (triggered by upstream DAG)
  - Task 1: `export_gold_tables` → `PythonOperator` dùng DuckDB `postgres_scanner` ATTACH PostgreSQL, CREATE OR REPLACE TABLE cho 4 gold tables, retry 3 lần
  - Task 2-5: `verify_dim_countries`, `verify_dim_indicators`, `verify_dim_dates`, `verify_fact_economic_indicators` → `SQLExecuteQueryOperator` đếm SELECT COUNT(*) trong PostgreSQL gold schema
  - Task 1 chạy trước, sau đó 4 task verify chạy song song
  - retries=2, retry_delay=2min

- [x] 4.6.2 Test DAG
  - Auto-triggered từ `run_dbt_transform` → export + 4 verify tasks success
  - Verified: gold.dim_countries (10), gold.dim_indicators (32), gold.dim_dates (29,585), gold.fact_economic_indicators (2,737)

---

## 4.7 Error handling & alerting (1 ngày)

- [x] 4.7.1 Cấu hình retry cho từng DAG
  - Ingest DAGs: retries=3, retry_delay=5min
  - Transform DAG: retries=1 (dbt có retry nội bộ), retry_delay=2min
  - Export DAG: retries=2, retry_delay=2min
  - `email_on_failure=False` (chưa cấu hình SMTP)

- [x] 4.7.2 Error handling trong code
  - DuckDB connection retry (3 lần) trong `_export_gold`
  - dbt test results parsing + raise RuntimeError nếu có failures
  - MinIO health check trước khi ingest

- [x] 4.7.3 Resource limits tuning
  - Airflow container: 5GB mem, 2 CPU (tăng từ 3GB sau khi gặp OOM với dbt tasks)
  - PARALLELISM=1 để tránh nhiều task subprocess đồng thời gây OOM

- [x] 4.7.4 Verify log hiển thị trong Airflow UI
  - Tất cả task logs đều hiển thị trong UI
  - Log format JSON structured, dễ parse

---

## 4.8 DAG dependency wiring (0.5 ngày)

- [x] 4.8.1 Cấu hình cross-DAG dependency
  - `ingest_world_bank` → trigger `run_dbt_transform` qua `TriggerDagRunOperator`
  - `ingest_world_bank_docs` → trigger `run_dbt_transform` qua `TriggerDagRunOperator` (`trigger_rule="none_failed"`)
  - `run_dbt_transform` → trigger `export_gold_to_postgres` qua `TriggerDagRunOperator`

- [x] 4.8.2 Set `max_active_runs=1` cho tất cả DAGs
- [x] 4.8.3 E2E test: trigger `run_dbt_transform` manual → auto-triggers `export_gold_to_postgres` → tất cả tasks pass

---

## Tổng: 33 checklist items | ~5-6 ngày

**Kết quả:** Airflow 3.0.6 hoạt động với 4 DAGs. Pipeline E2E: MinIO Bronze → DuckDB/dbt Silver → DuckDB Gold → PostgreSQL Gold. Cross-DAG triggers hoàn chỉnh. 34 dbt tests pass. 4 gold tables trong PostgreSQL với dữ liệu (10 countries, 32 indicators, 29,585 dates, 2,737 facts).

**Next: [Phase 5 — Serving & Intelligence](05-intelligence.md)**
