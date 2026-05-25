# Data Model — Intelligent Data Platform (IDP)

> **Status: Design / Blueprint**. Defines the target table schemas across Bronze, Silver, and Gold layers.
> Every table here maps to a planned dbt model file. Implementation pending.

---

## 1. Medallion Architecture Overview

```
┌─────────────────────┐     ┌─────────────────────┐     ┌─────────────────────┐
│       BRONZE        │     │       SILVER        │     │        GOLD         │
│                     │     │                     │     │                     │
│  Raw, as-ingested   │────►│  Cleaned, typed,    │────►│  Business-ready,    │
│  Append-only        │     │  deduplicated       │     │  aggregated, joined │
│  Parquet in MinIO   │     │  Parquet in MinIO   │     │  PostgreSQL tables  │
│                     │     │  (DuckDB views)     │     │                     │
└─────────────────────┘     └─────────────────────┘     └─────────────────────┘

Storage:  MinIO (S3)          MinIO (S3) / DuckDB       PostgreSQL 16
Format:   Parquet             Parquet                   Relational tables
Tool:     Python scripts      dbt + DuckDB              dbt + DuckDB → PG export
Testing:  None                dbt tests (basic)         dbt tests (full)
```

---

## 2. Naming Conventions

| Layer | Prefix | Example | dbt Directory |
|---|---|---|---|
| Bronze | `raw_` | `raw_world_bank_indicators` | N/A (external source in MinIO) |
| Silver (staging) | `stg_` | `stg_world_bank__indicators` | `models/staging/` |
| Gold (dimensions) | `dim_` | `dim_countries` | `models/marts/` |
| Gold (facts) | `fact_` | `fact_economic_indicators` | `models/marts/` |

**dbt model naming pattern:** `stg_{source}__{entity}` for staging, `dim_{entity}` or `fact_{entity}` for marts.

---

## 3. Bronze Layer (Raw)

Bronze = exact copy of source data with minimal metadata added. Stored as Parquet in MinIO.

### 3.1 `raw_world_bank_indicators`

| Column | Type | Source | Description |
|---|---|---|---|
| `country_code` | STRING | API | ISO 3-letter country code |
| `country_name` | STRING | API | Full country name |
| `indicator_code` | STRING | API | World Bank indicator ID |
| `indicator_name` | STRING | API | Human-readable indicator name |
| `year` | INT | API | Observation year |
| `value` | FLOAT | API | Indicator value (nullable) |
| `_ingested_at` | TIMESTAMP | System | Ingestion timestamp |
| `_source` | STRING | System | Always "world_bank" |

**Path:** `s3://bronze/world_bank/indicators/year={YYYY}/data.parquet`

### 3.2 `raw_world_bank_docs` (metadata)

| Column | Type | Source | Description |
|---|---|---|---|
| `doc_id` | STRING | API | Unique document identifier |
| `title` | STRING | API | Document title |
| `abstract` | STRING | API | Short abstract or summary |
| `display_date` | STRING | API | Publication date |
| `doc_type` | STRING | API | working-paper, report, brief, etc. |
| `pdf_url` | STRING | API | Direct PDF download URL |
| `countries` | STRING | API | Semicolon-separated country names |
| `topics` | STRING | API | Semicolon-separated topic names |
| `language` | STRING | API | Document language |
| `_ingested_at` | TIMESTAMP | System | Ingestion timestamp |
| `_source` | STRING | System | Always "world_bank_docs" |

**Path:** `s3://bronze/world_bank_docs/metadata/documents.parquet`

### 3.3 `raw_world_bank_docs_chunks` (text chunks)

| Column | Type | Source | Description |
|---|---|---|---|
| `doc_id` | STRING | Derived | Parent document identifier |
| `chunk_id` | STRING | System | MD5 hash |
| `chunk_index` | INT | System | Position within document |
| `text` | STRING | PDF extraction | Chunk text (~1500 chars) |
| `title` | STRING | API | Document title (denormalized) |
| `display_date` | STRING | API | Publication date |
| `doc_type` | STRING | API | Document type |
| `countries` | STRING | API | Countries |
| `topics` | STRING | API | Topics |
| `language` | STRING | API | Language |
| `_ingested_at` | TIMESTAMP | System | Ingestion timestamp |
| `_source` | STRING | System | Always "world_bank_docs" |

**Path:** `s3://bronze/world_bank_docs/chunks/chunks.parquet`

---

## 4. Silver Layer (Staging)

Silver = cleaned, typed, deduplicated, standardized. Each staging model reads from Bronze (Parquet via DuckDB) and outputs clean data.

### 4.1 `stg_world_bank__indicators`

| Column | Type | Transformation | Description |
|---|---|---|---|
| `country_code` | VARCHAR(3) | UPPER(trim) | ISO 3-letter code |
| `country_name` | VARCHAR | trim | Country name |
| `indicator_code` | VARCHAR | trim | Indicator ID |
| `indicator_name` | VARCHAR | trim | Indicator name |
| `year` | INTEGER | cast | Observation year |
| `value` | DOUBLE | cast, filter nulls | Indicator value |
| `ingested_at` | TIMESTAMP | rename | When ingested |

**Transformations:** remove NULL values, trim whitespace, cast types, deduplicate on (country_code, indicator_code, year).

---

## 5. Gold Layer (Marts)

Gold = business-ready tables in PostgreSQL. Dimensional model (star schema) for easy querying.

### 5.1 Dimension Tables

#### `dim_countries`

| Column | Type | PK | Description |
|---|---|---|---|
| `country_key` | SERIAL | ✓ | Surrogate key |
| `country_code` | VARCHAR(3) | | ISO 3-letter code (natural key) |
| `country_name` | VARCHAR | | Full name |
| `region` | VARCHAR | | World Bank region |
| `income_group` | VARCHAR | | Low / Lower-middle / Upper-middle / High |
| `is_asean` | BOOLEAN | | ASEAN member flag |
| `is_primary` | BOOLEAN | | Primary focus country (Vietnam) |

**Source:** World Bank country metadata + seed file.

#### `dim_indicators`

| Column | Type | PK | Description |
|---|---|---|---|
| `indicator_key` | SERIAL | ✓ | Surrogate key |
| `indicator_code` | VARCHAR | | Original source code |
| `indicator_name` | VARCHAR | | Human-readable name |
| `source_system` | VARCHAR | | Source: world_bank, nso_vietnam, fred |
| `category` | VARCHAR | | gdp / prices / trade / rates / labor / investment / structure / technology |
| `unit` | VARCHAR | | %, USD, Index, etc. |
| `frequency` | VARCHAR | | annual / quarterly / monthly / daily / sparse |
| `description` | TEXT | | Detailed description |

**Natural key:** (`indicator_code`, `source_system`). Cùng một indicator code có thể tồn tại ở nhiều nguồn (vd: GDP từ World Bank và GDP từ NSO).

**Source:** Seed file + derived from staging models.

#### `dim_dates`

| Column | Type | PK | Description |
|---|---|---|---|
| `date_key` | INTEGER | ✓ | YYYYMMDD format |
| `full_date` | DATE | | Actual date |
| `year` | INTEGER | | Year |
| `quarter` | INTEGER | | Quarter (1-4) |
| `month` | INTEGER | | Month (1-12) |
| `month_name` | VARCHAR | | January, February, etc. |
| `day_of_week` | INTEGER | | 1=Monday, 7=Sunday |
| `is_weekend` | BOOLEAN | | Saturday/Sunday |
| `is_vietnam_holiday` | BOOLEAN | | Vietnamese public holidays |
| `fiscal_year_vn` | INTEGER | | Vietnam fiscal year (= calendar year) |

**Source:** Generated (dbt seed or macro), range 1950-01-01 to 2030-12-31. FRED có dữ liệu từ 1950s nên cần range rộng hơn.

---

### 5.2 Fact Tables

#### `fact_economic_indicators`

The central fact table — all economic indicators unified.

| Column | Type | FK | Description |
|---|---|---|---|
| `indicator_key` | INTEGER | → dim_indicators | Indicator reference |
| `country_key` | INTEGER | → dim_countries | Country reference |
| `date_key` | INTEGER | → dim_dates | Date reference |
| `period_start` | DATE | | Period start date |
| `period_end` | DATE | | Period end date |
| `value` | DOUBLE PRECISION | | Indicator value |
| `source_system` | VARCHAR | | Source: world_bank, nso_vietnam, fred |
| `loaded_at` | TIMESTAMP | | When loaded to Gold |

**Grain:** One row per indicator × country × period × source_system.

**Sources merged:**
- `stg_world_bank__indicators` → 32 economic indicators by country (annual)
- `stg_nso__indicators` (planned — Expand phase) → domestic indicators (quarterly/monthly)
- `stg_fred__series` (planned — Expand phase) → US/global context indicators (daily/weekly/monthly)

### 5.3 Multi-Source Conflict Resolution

Khi nhiều nguồn cùng cung cấp một chỉ tiêu cho cùng quốc gia và cùng thời điểm, áp dụng quy tắc sau:

| Rule | Priority | Example |
|---|---|---|
| **Nguồn gốc ưu tiên** | NSO > World Bank cho dữ liệu Vietnam | GDP Vietnam từ NSO được coi là authoritative hơn World Bank |
| **Không merge** | Mỗi nguồn luôn giữ `source_system` riêng | Row WorldBank và row NSO cùng tồn tại trong fact table |
| **Granularity khác nhau** | Giữ nguyên grain gốc, không suy luận | Monthly CPI từ NSO không bị aggregate lên annual để match World Bank |
| **Conflict flag** | Thêm view `gold.conflicting_indicators` để detect | Query detect 2 row khác value > 5% cho cùng indicator × country × year |

**API behavior:** Khi query indicator không chỉ định `source_system`, API trả về nguồn ưu tiên (NSO cho Vietnam, World Bank cho global). Khi chỉ định `?source_system=all`, trả về tất cả nguồn.

---

## 6. Entity Relationship Diagram

```
                    ┌──────────────────┐
                    │   dim_dates      │
                    │                  │
                    │  date_key (PK)   │
                    │  full_date       │
                    │  year, quarter   │
                    │  month, ...      │
                    └────────┬─────────┘
                             │
                             ▼
              ┌──────────────────────────────┐
              │ fact_economic_indicators     │
              │                              │
              │ indicator_key (FK)           │
              │ country_key (FK)             │
              │ date_key (FK)                │
              │ value                        │
              │ source_system                │
              └───┬──────────┬───────────────┘
                  │          │
                  ▼          ▼
          ┌────────┐   ┌────────────┐
          │dim_    │   │dim_        │
          │indica- │   │countries   │
          │tors    │   │            │
          │        │   │country_key │
          │indica- │   │country_code│
          │tor_key │   │region      │
          │source_ │   │income_group│
          │system  │   │is_asean    │
          └────────┘   └────────────┘
```

---

## 7. dbt Model Dependency Graph (DAG)

```
Bronze (MinIO Parquet)
    │
    ├── stg_world_bank__indicators ──┐
    ├── stg_nso__indicators ─────────┤ (Expand phase)
    ├── stg_fred__series ────────────┤ (Expand phase)
    │                                ├── dim_indicators (seed + WB + NSO + FRED)
    │                                ├── dim_countries (seed + WB metadata)
    │                                └── dim_dates (generated, 1950-2030)
    │                                     │
    │                                     └── fact_economic_indicators
    │                                           │  (unified, source_system column)
    │                                           └──► PostgreSQL (Gold schema)
    │
    └── (raw_wb_docs → chunks) ────────► directly read by embeddings pipeline
                                          (via MinIO boto3, not dbt)
```

---

## 8. Materialization Strategy

| Model Type | dbt Materialization | Storage | Reason |
|---|---|---|---|
| Staging (`stg_*`) | `view` | DuckDB in-memory | Fast, no disk needed, rebuilt each run |
| Marts (`dim_*`, `fact_*`) | `table` | DuckDB → export to PostgreSQL | Persistent, queryable by apps |

**Export to PostgreSQL via `transform/export_gold.py`** using DuckDB postgres extension.

---

## 9. Seed Files

Static reference data managed as dbt seeds (CSV in `transform/dbt/seeds/`):

| Seed File | Purpose | Rows (approx) |
|---|---|---|
| `seed_countries.csv` | Country codes, names, regions, flags | ~10 rows |
| `seed_indicators.csv` | Indicator codes, names, categories, units | ~32 rows |

---

## 10. Data Volume Estimates

| Table | Rows (initial) | Growth Rate |
|---|---|---|
| `dim_countries` | ~10 | Static |
| `dim_indicators` | ~32 | Slow (new indicators) |
| `dim_dates` | ~29,000 | None (pre-generated, 1950-2030) |
| `fact_economic_indicators` | ~8,000 | ~320 rows/year (32 indicators × 10 countries, World Bank annual). Will grow as NSO and FRED sources are added. |
| **Total Gold** | | **< 5 MB** |

> Data volume is tiny. DuckDB and PostgreSQL will handle this effortlessly.

---

## 11. PostgreSQL Schema Layout

```sql
-- Gold layer (business-ready)
CREATE SCHEMA gold;

-- Tables in gold schema:
-- gold.dim_countries
-- gold.dim_indicators
-- gold.dim_dates
-- gold.fact_economic_indicators

-- Embeddings (RAG)
CREATE SCHEMA embeddings;

-- embeddings.economic_embeddings (pgvector)
--   Stores embeddings from:
--     - fact_economic_indicators (type: economic_indicator)
--     - World Bank Documents chunks (type: world_bank_report)
```

---

## 12. Key Design Decisions

| # | Decision | Choice | Rationale |
|---|---|---|---|
| 1 | Dimensional model (star schema) | Yes | Simple, fast queries, easy for BI/AI to consume |
| 2 | Surrogate keys | Yes (SERIAL) | Decouple from source system IDs |
| 3 | Unified fact table for indicators | Yes | All sources merged into one queryable table |
| 4 | dim_dates pre-generated | Yes | Standard practice, enables time-based analysis |
| 5 | Staging as views (not tables) | Yes | Saves disk, DuckDB is fast enough |
| 6 | Gold in PostgreSQL (not DuckDB) | Yes | Persistent, concurrent access, pgvector for RAG |
| 7 | Documents embedded directly from MinIO | Yes | Bypasses dbt; embedding pipeline reads chunks via boto3 |
| 8 | Minimal dimensions | Yes | Start small, add columns as needed |
| 9 | Multi-source conflict resolution | NSO > World Bank for domestic data | Each source keeps its own rows; API defaults to authoritative source per country |
