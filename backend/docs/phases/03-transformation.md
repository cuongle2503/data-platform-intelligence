# Phase 3: Transformation — DuckDB + dbt

> **Status: ✅ Done (verified 2026-05-20) | Duration: ~11-13 ngày | Core của platform**

---

## Mục tiêu

DuckDB đọc Parquet từ MinIO → dbt transform Bronze → Silver → Gold → export PostgreSQL. Có dbt tests + auto-generated docs.

---

## 3.1 PostgreSQL bootstrap (1 ngày)

- [x] 3.1.1 Thêm PostgreSQL service vào `docker-compose.yml`
  - service `postgres`:
    - image `pgvector/pgvector:pg16`
    - port `5432:5432`
    - volume `pg_data:/var/lib/postgresql/data`
    - env `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` từ `.env`
    - healthcheck `pg_isready -U $POSTGRES_USER -d $POSTGRES_DB`
    - resource limit: 4GB mem, 2 CPU
    - restart `unless-stopped`
    - network `idp-backend`

- [x] 3.1.2 Tạo init SQL `infra/scripts/init-postgres.sql`
  - `CREATE DATABASE airflow_db;`
  - `CREATE USER airflow WITH PASSWORD '<password>';`
  - `GRANT ALL PRIVILEGES ON DATABASE airflow_db TO airflow;`
  - `\c idp_warehouse;`
  - `CREATE EXTENSION IF NOT EXISTS vector;`
  - `CREATE SCHEMA IF NOT EXISTS gold;`
  - `CREATE SCHEMA IF NOT EXISTS embeddings;`
  - `CREATE ROLE readonly_role;`
  - `CREATE ROLE api_service WITH LOGIN PASSWORD '<password>';`
  - `GRANT readonly_role TO api_service;`

- [x] 3.1.3 Mount init script vào `/docker-entrypoint-initdb.d/`
- [x] 3.1.4 Start: `docker compose --env-file .env up -d`
- [x] 3.1.5 Verify: `psql -h localhost -U idp_admin -d idp_warehouse -c "\dx"` → thấy `vector`
- [x] 3.1.6 Verify schemas: `\dn` → thấy `gold`, `embeddings`

---

## 3.2 Khởi tạo dbt project (2 ngày)

- [x] 3.2.1 Init dbt project
  - `mkdir -p transform/dbt`
  - `cd transform/dbt && dbt init idp_transform` (chọn duckdb adapter)
  - Hoặc manual: tạo `dbt_project.yml` + `profiles.yml`

- [x] 3.2.2 Cấu hình `dbt_project.yml`
  - name: `idp_transform`
  - profile: `idp_duckdb`
  - models: `transform/dbt/models`
  - seeds: `transform/dbt/seeds`
  - tests: `transform/dbt/tests`
  - macros: `transform/dbt/macros`

- [x] 3.2.3 Cấu hình `profiles.yml` cho DuckDB đọc MinIO
  - type: `duckdb`
  - path: `tmp/duckdb/idp.db`
  - extensions: `[httpfs]`
  - `s3_endpoint`: từ env `DUCKDB_S3_ENDPOINT`
  - `s3_access_key`, `s3_secret_key` từ env
  - `s3_use_ssl`: false
  - `s3_url_style`: path

- [x] 3.2.4 Test connection
  - `cd transform/dbt && dbt debug` → All checks passed
  - Test SQL: DuckDB đọc được Parquet từ MinIO

- [x] 3.2.5 Tạo `models/staging/_sources.yml`
  - Source `bronze`:
    - table `world_bank_indicators` → `s3://bronze/world_bank/indicators/**/*.parquet`
    - table `world_bank_docs_metadata` → `s3://bronze/world_bank_docs/metadata/*.parquet`
    - table `world_bank_docs_chunks` → `s3://bronze/world_bank_docs/chunks/*.parquet`

---

## 3.3 Staging models (1.5 ngày)

- [x] 3.3.1 Tạo `models/staging/stg_world_bank__indicators.sql`
  - SELECT từ source `bronze.world_bank_indicators`
  - Transform: UPPER(TRIM(country_code)), TRIM(country_name), TRIM(indicator_code), TRIM(indicator_name)
  - CAST(year AS INTEGER), CAST(value AS DOUBLE)
  - WHERE value IS NOT NULL
  - RENAME `_ingested_at` → `ingested_at`
  - DEDUPLICATE: ROW_NUMBER() OVER (PARTITION BY country_code, indicator_code, year ORDER BY ingested_at DESC) = 1

- [x] 3.3.2 Tạo `models/staging/stg_world_bank__docs_metadata.sql`
  - SELECT từ `bronze.world_bank_docs_metadata`
  - TRIM các cột text, CAST date, lọc NULL doc_id

- [x] 3.3.3 Tạo `models/staging/stg_world_bank__docs_chunks.sql`
  - SELECT từ `bronze.world_bank_docs_chunks`
  - JOIN metadata để lấy doc_type, countries, topics
  - Filter chunk text NOT NULL AND LENGTH(text) > 0

- [x] 3.3.4 Tạo `models/staging/_staging.yml`
  - Column descriptions + tests (not_null, unique) cho từng staging model

- [x] 3.3.5 Chạy thử
  - `dbt run --select staging` → tất cả staging models thành công

---

## 3.4 Seed files (0.5 ngày)

- [x] 3.4.1 Tạo `seeds/seed_countries.csv`
  - Columns: country_code, country_name, region, income_group, is_asean, is_primary
  - ~10 rows cho 10 quốc gia quan tâm (có thể mở rộng sau)

- [x] 3.4.2 Tạo `seeds/seed_indicators.csv`
  - Columns: indicator_code, indicator_name, category, unit, frequency, description
  - ~32 rows cho 32 indicators từ source catalog

- [x] 3.4.3 Tạo `macros/generate_date_dim.sql`
  - Macro nhận start_date, end_date → generate dim_dates
  - Có is_vietnam_holiday (hardcode hoặc CSV lookup)

- [x] 3.4.4 `dbt seed` → seeds loaded thành công

---

## 3.5 Mart models — Dimensions (1 ngày)

- [x] 3.5.1 Tạo `models/marts/dim_countries.sql`
  - SELECT từ `seed_countries`
  - Thêm `country_key` = ROW_NUMBER() (SERIAL khi export PG)
  - LEFT JOIN stg indicators để enrich region/income_group từ World Bank metadata nếu có

- [x] 3.5.2 Tạo `models/marts/dim_indicators.sql`
  - SELECT từ `seed_indicators`
  - Thêm `indicator_key` = ROW_NUMBER()

- [x] 3.5.3 Tạo `models/marts/dim_dates.sql`
  - Gọi macro `generate_date_dim('1950-01-01', '2030-12-31')`
  - Thêm `date_key` = YYYYMMDD format

- [x] 3.5.4 Tạo `models/marts/_marts.yml`
  - not_null tests trên tất cả primary keys
  - unique tests trên natural keys (country_code, indicator_code, date_key)

---

## 3.6 Mart models — Facts (1.5 ngày)

- [x] 3.6.1 Tạo `models/marts/fact_economic_indicators.sql`
  - SELECT từ `stg_world_bank__indicators`
  - JOIN `dim_countries` ON country_code → lấy country_key
  - JOIN `dim_indicators` ON indicator_code AND source_system = 'world_bank' → lấy indicator_key
  - JOIN `dim_dates` ON year → lấy date_key (annual grain → date_key = YYYY0101)
  - Columns: indicator_key, country_key, date_key, period_start, period_end, value, source_system, loaded_at
  - source_system = 'world_bank' (sẽ mở rộng join với NSO, FRED ở Expand phase)
  - period_start = MAKE_DATE(year, 1, 1), period_end = MAKE_DATE(year, 12, 31)

- [x] 3.6.2 Tạo `tests/assert_gdp_range.sql`
  - GDP indicators (NY.GDP.*) nên có value > 0

- [x] 3.6.3 Tạo `tests/assert_no_future_dates.sql`
  - Không có date_key nào vượt quá current_date

- [x] 3.6.4 `dbt run --select marts` → tất cả 4 mart models thành công

---

## 3.7 Export Gold → PostgreSQL (1 ngày)

- [x] 3.7.1 Tạo `exports/export_gold_to_pg.py`
  - Dùng DuckDB postgres_scanner extension
  - `ATTACH 'postgresql://...' AS pg (TYPE postgres)`
  - FOR mỗi mart model: CREATE OR REPLACE TABLE pg.gold.<table> AS SELECT * FROM <model>
  - Xử lý lỗi connection, retry 3 lần

- [x] 3.7.2 Test export
  - Chạy script → verify data trong PostgreSQL
  - `SELECT COUNT(*) FROM gold.fact_economic_indicators` → > 0
  - Verify foreign key integrity (JOIN với dim tables)

---

## 3.8 dbt tests & docs (2 ngày)

- [x] 3.8.1 Chạy full test suite
  - `dbt test` → tất cả pass
  - Fix nếu có test fail

- [x] 3.8.2 Thêm accepted_values tests
  - `dim_countries.is_asean` IN (true, false)
  - `dim_indicators.frequency` IN ('annual', 'sparse')
  - `dim_indicators.category` IN danh sách categories

- [x] 3.8.3 Thêm relationship tests
  - `fact_economic_indicators.indicator_key` → `dim_indicators.indicator_key`
  - `fact_economic_indicators.country_key` → `dim_countries.country_key`
  - `fact_economic_indicators.date_key` → `dim_dates.date_key`

- [x] 3.8.4 Generate docs
  - `dbt docs generate`
  - Host docs locally: `dbt docs serve --port 8081`
  - Verify lineage DAG hiển thị đúng trong browser

- [x] 3.8.5 Viết thêm custom tests nếu cần
  - CPI values trong khoảng [-50, 1000]
  - Population > 0
  - GDP per capita trong khoảng hợp lý (100 - 200000)

---

## Tổng: 39 checklist items | ~11-13 ngày

**Next: [Phase 4 — Orchestration](04-orchestration.md)**
