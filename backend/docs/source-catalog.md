# Source Catalog — Intelligent Data Platform (IDP)

> **Status: Design / Blueprint**. Inventory of all planned data sources.
> Each entry documents: what data, where to get it, how to authenticate, what format, and how often to pull.
> Connector scripts referenced are planned; implementation pending.

---

## 1. Source Overview

| # | Source | Provider | Data Domain | Frequency | Phase | Connector |
|---|---|---|---|---|---|---|
| 1 | World Bank Open Data | World Bank | Global economic indicators (32 indicators) | Monthly | 1 | Python (requests) |
| 2 | World Bank Documents | World Bank | Reports, working papers (text) | Monthly | Expand | Python (requests, server-side text extraction) |
| 3 | NSO Vietnam | Tổng cục Thống kê VN | Domestic economic indicators (quarterly) | Monthly | Expand | Python (requests) |
| 4 | FRED | US Federal Reserve | US + global context indicators | Weekly | Expand | Python (fredapi) |

---

## 2. World Bank Open Data

### 2.1 Overview

| Field | Value |
|---|---|
| Provider | The World Bank |
| API Base URL | `https://api.worldbank.org/v2` |
| Authentication | None (public API, no key required) |
| Rate Limit | ~30 requests/second (undocumented, be conservative) |
| Documentation | https://datahelpdesk.worldbank.org/knowledgebase/articles/889392 |
| Data License | Creative Commons Attribution 4.0 (CC BY 4.0) |

### 2.2 Indicators of Interest (32 indicators)

**GDP & Income**

| Indicator Code | Name | Unit | Frequency |
|---|---|---|---|
| `NY.GDP.MKTP.CD` | GDP (current US$) | USD | Annual |
| `NY.GDP.MKTP.KD.ZG` | GDP growth (annual %) | % | Annual |
| `NY.GDP.PCAP.CD` | GDP per capita (current US$) | USD | Annual |
| `NY.GNP.PCAP.CD` | GNI per capita (current US$) | USD | Annual |

**Prices & Inflation**

| Indicator Code | Name | Unit | Frequency |
|---|---|---|---|
| `FP.CPI.TOTL.ZG` | Inflation, consumer prices (annual %) | % | Annual |
| `FP.CPI.TOTL` | Consumer Price Index (2010=100) | Index | Annual |

**Labor**

| Indicator Code | Name | Unit | Frequency |
|---|---|---|---|
| `SL.UEM.TOTL.ZS` | Unemployment, total (% of labor force) | % | Annual |
| `SL.TLF.TOTL.IN` | Labor force, total | Count | Annual |

**Trade & Investment**

| Indicator Code | Name | Unit | Frequency |
|---|---|---|---|
| `BX.KLT.DINV.WD.GD.ZS` | FDI, net inflows (% of GDP) | % | Annual |
| `NE.EXP.GNFS.ZS` | Exports of goods and services (% of GDP) | % | Annual |
| `NE.IMP.GNFS.ZS` | Imports of goods and services (% of GDP) | % | Annual |
| `BN.CAB.XOKA.GD.ZS` | Current account balance (% of GDP) | % | Annual |

**Finance**

| Indicator Code | Name | Unit | Frequency |
|---|---|---|---|
| `GC.DOD.TOTL.GD.ZS` | Central government debt (% of GDP) | % | Annual |
| `FI.RES.TOTL.CD` | Total reserves (current US$) | USD | Annual |
| `PA.NUS.FCRF` | Official exchange rate (LCU per US$) | Rate | Annual |

**Population & Society**

| Indicator Code | Name | Unit | Frequency |
|---|---|---|---|
| `SP.POP.TOTL` | Population, total | Count | Annual |
| `SP.POP.GROW` | Population growth (annual %) | % | Annual |
| `SI.POV.GINI` | Gini index | Index | Sparse |

**Education & Technology**

| Indicator Code | Name | Unit | Frequency |
|---|---|---|---|
| `SE.PRM.ENRR` | School enrollment, primary (% gross) | % | Annual |
| `IT.NET.USER.ZS` | Internet users (% of population) | % | Annual |

**Infrastructure & Environment**

| Indicator Code | Name | Unit | Frequency |
|---|---|---|---|
| `EG.USE.ELEC.KH.PC` | Electric power consumption (kWh per capita) | kWh/capita | Annual |
| `EN.ATM.CO2E.KT` | CO2 emissions (kt) | kt | Annual |

**Economic Structure**

| Indicator Code | Name | Unit | Frequency |
|---|---|---|---|
| `NV.AGR.TOTL.ZS` | Agriculture, value added (% of GDP) | % | Annual |
| `NV.IND.TOTL.ZS` | Industry, value added (% of GDP) | % | Annual |
| `NV.SRV.TOTL.ZS` | Services, value added (% of GDP) | % | Annual |

**Trade & Infrastructure**

| Indicator Code | Name | Unit | Frequency |
|---|---|---|---|
| `LP.LPI.OVRL.XQ` | Logistics Performance Index | Index | Sparse |
| `TM.TAX.MRCH.SM.AR` | Tariff rate, MFN simple mean | % | Annual |
| `IT.CEL.SETS.P2` | Mobile cellular subscriptions (per 100) | per 100 | Annual |
| `IT.NET.BBND.P2` | Fixed broadband subscriptions (per 100) | per 100 | Annual |
| `GB.XPD.RSDV.GD.ZS` | R&D expenditure (% of GDP) | % | Annual |
| `SL.TLF.CACT.FE.ZS` | Female labor force participation rate | % | Annual |
| `ST.INT.RCPT.CD` | International tourism receipts (USD) | USD | Annual |

### 2.3 Countries of Interest

| Code | Country | Priority |
|---|---|---|
| `VNM` | Vietnam | Primary |
| `THA` | Thailand | Comparison |
| `IDN` | Indonesia | Comparison |
| `PHL` | Philippines | Comparison |
| `MYS` | Malaysia | Comparison |
| `SGP` | Singapore | Comparison |
| `CHN` | China | Context |
| `USA` | United States | Context |
| `JPN` | Japan | Context |
| `KOR` | South Korea | Context |

### 2.4 Extraction Logic

```python
# Metadata-only (default)
python -m ingestion.connectors.world_bank.main
```

### 2.5 Output Schema (Bronze)

| Column | Type | Description |
|---|---|---|
| `country_code` | STRING | ISO 3-letter code |
| `country_name` | STRING | Full country name |
| `indicator_code` | STRING | World Bank indicator ID |
| `indicator_name` | STRING | Human-readable name |
| `year` | INT | Year of observation |
| `value` | FLOAT | Indicator value |
| `_ingested_at` | TIMESTAMP | When data was pulled |

### 2.6 Storage Path

```
s3://bronze/world_bank/indicators/year={YYYY}/data.parquet
```

---

## 3. World Bank Documents & Reports (WDS)

### 3.1 Overview

| Field | Value |
|---|---|
| Provider | The World Bank |
| API Base URL | `https://search.worldbank.org/api/v2/wds` |
| Authentication | None (public API, no key required) |
| Rate Limit | Be conservative — ~10 requests/minute |
| Documentation | https://documents.worldbank.org/en/publication/documents-reports/api |
| Data License | Creative Commons Attribution 4.0 (CC BY 4.0) |

### 3.2 Data of Interest

| Search Query | Document Type | Purpose | Frequency |
|---|---|---|---|
| `countrycode_exact=VN` | All | All reports about Vietnam | Monthly |
| `countrycode_exact=VN` + `docty=working-paper` | Working Papers | Academic research | Monthly |
| `q=Vietnam economic outlook` | Reports, Updates | Economic forecasts | Quarterly |
| `q=East Asia Pacific economic update` | Reports | Regional context | Quarterly |
| `q=ASEAN trade development` | Reports | Trade analysis | Quarterly |

### 3.3 Extraction Strategy

The connector calls the WDS search API with predefined queries, deduplicates results, and stores document metadata as Parquet. When `--full-text` is enabled, it fetches server-extracted text via the World Bank `/text/` endpoint (converting `/pdf/...pdf` → `/text/...txt`), avoiding local PDF parsing entirely. Text is then chunked into overlapping segments (~1500 chars with 200-char overlap at paragraph boundaries). Server-side extraction yields ~70% more characters and preserves whitespace better than local PDF parsing.

```python
# Metadata-only (default)
python -m ingestion.connectors.world_bank_docs.main

# With full text extraction
python -m ingestion.connectors.world_bank_docs.main --full-text
```

### 3.4 Output Schema (Bronze) — Metadata

| Column | Type | Description |
|---|---|---|
| `doc_id` | STRING | Unique document identifier |
| `title` | STRING | Document title |
| `abstract` | STRING | Short abstract or summary |
| `display_date` | STRING | Publication date |
| `doc_type` | STRING | Document type (working-paper, report, etc.) |
| `pdf_url` | STRING | Direct PDF download URL |
| `countries` | STRING | Semicolon-separated country names |
| `topics` | STRING | Semicolon-separated topic names |
| `language` | STRING | Document language |
| `_ingested_at` | TIMESTAMP | When data was pulled |

### 3.5 Output Schema (Bronze) — Chunks (with --full-text)

| Column | Type | Description |
|---|---|---|
| `doc_id` | STRING | Parent document identifier |
| `chunk_id` | STRING | Unique chunk identifier (MD5 hash) |
| `chunk_index` | INT | Position within document |
| `text` | STRING | Chunk text (~1500 chars) |
| `title` | STRING | Document title (denormalized) |
| `display_date` | STRING | Publication date (denormalized) |
| `doc_type` | STRING | Document type (denormalized) |
| `countries` | STRING | Countries (denormalized) |
| `topics` | STRING | Topics (denormalized) |
| `language` | STRING | Language (denormalized) |
| `_ingested_at` | TIMESTAMP | When data was pulled |

### 3.6 Storage Path

```
s3://bronze/world_bank_docs/metadata/documents.parquet
s3://bronze/world_bank_docs/chunks/chunks.parquet
```

### 3.7 Known Challenges

| Challenge | Mitigation |
|---|---|
| Text fetch can be slow for many documents | Run with --full-text only when updating embeddings |
| Text extraction quality depends on server-side availability | Retry with exponential backoff for 403/429/502/503/504 |
| API may return duplicates across queries | Deduplicate by doc_id |
| Some documents lack PDF URLs | Store metadata regardless; skip PDF extraction gracefully |

---

## 4. NSO Vietnam (Tổng cục Thống kê)

> **Status: Planned — Expand Phase.** Implementation pending.

### 4.1 Overview

| Field | Value |
|---|---|
| Provider | Tổng cục Thống kê Việt Nam (GSO) |
| API Base URL | `https://api.gso.gov.vn/v1` (PX-Web API) |
| Authentication | API key required (apply via GSO portal) |
| Rate Limit | Unknown, assume conservative (~10 requests/minute) |
| Documentation | https://www.gso.gov.vn/en/px-web/ |
| Data License | Government open data (terms TBD) |
| **Risk Level** | ⚠️ Medium — API stability is inconsistent; format may change between releases |

### 4.2 Indicators of Interest

NSO publishes domestic indicators not available in World Bank. Exact indicator codes TBD during implementation.

| Domain | Expected Indicators | Frequency |
|---|---|---|
| National Accounts | GDP by industry, GDP growth rate | Quarterly |
| CPI | Consumer Price Index (monthly, by province) | Monthly |
| Trade | Import/Export value by commodity | Monthly |
| Labor | Employment rate, labor force participation | Quarterly |
| Population | Census updates, population estimates | Annual |

### 4.3 Known Risks

| Risk | Mitigation |
|---|---|
| API offline without notice | Retry with exponential backoff (3 attempts, 5min gaps); alert on persistent failure |
| Format changes between releases | Schema validation before upload; fail loudly on mismatch |
| Metadata in Vietnamese only | Maintain mapping table for indicator codes ↔ English names |
| API key procurement delay | Start World Bank + FRED first; NSO is Expand phase |

### 4.4 Output Schema (Bronze)

Mirrors the World Bank indicator schema for consistency:

| Column | Type | Description |
|---|---|---|
| `country_code` | STRING | Always "VNM" |
| `country_name` | STRING | Always "Vietnam" |
| `indicator_code` | STRING | NSO indicator ID |
| `indicator_name` | STRING | Human-readable name (mapped to English) |
| `year` | INT | Observation year |
| `quarter` | INT | Quarter (1-4), NULL if annual |
| `value` | FLOAT | Indicator value |
| `_ingested_at` | TIMESTAMP | When data was pulled |
| `_source` | STRING | Always "nso_vietnam" |

### 4.5 Storage Path

```
s3://bronze/nso/indicators/year={YYYY}/data.parquet
```

---

## 5. FRED (Federal Reserve Economic Data)

> **Status: Planned — Expand Phase.** US macroeconomic data for global context and comparison.

### 5.1 Overview

| Field | Value |
|---|---|
| Provider | Federal Reserve Bank of St. Louis |
| API Base URL | `https://api.stlouisfed.org/fred` |
| Authentication | API key (free tier: 120 requests/min) |
| Rate Limit | 120 requests/minute (free tier) |
| Documentation | https://fred.stlouisfed.org/docs/api/fred/ |
| Data License | Public domain (US government data) |
| **Risk Level** | 🟢 Low — stable API, well-documented, free tier is generous |

### 5.2 Indicators of Interest

FRED provides US and international context indicators. Focus on global benchmarks relevant to Vietnam comparison.

| Indicator Code | Name | Purpose |
|---|---|---|
| `GDP` | Gross Domestic Product (US) | Global context |
| `CPIAUCSL` | Consumer Price Index (US) | Inflation benchmark |
| `FEDFUNDS` | Federal Funds Rate | Global interest rate context |
| `DEXVUS` | USD/VND Exchange Rate | Currency context |
| `T10YIE` | 10-Year Breakeven Inflation Rate | Inflation expectations |
| `WTISPLC` | Crude Oil Prices (WTI) | Commodity context |

### 5.3 Output Schema (Bronze)

Aligned with World Bank schema:

| Column | Type | Description |
|---|---|---|
| `country_code` | STRING | Always "USA" |
| `country_name` | STRING | Always "United States" |
| `indicator_code` | STRING | FRED series ID |
| `indicator_name` | STRING | Series title |
| `date` | DATE | Observation date (daily/monthly/quarterly) |
| `value` | FLOAT | Indicator value |
| `_ingested_at` | TIMESTAMP | When data was pulled |
| `_source` | STRING | Always "fred" |

### 5.4 Storage Path

```
s3://bronze/fred/series_id={SERIES_ID}/data.parquet
```

---

## 6. Ingestion Schedule Summary

| Source | Frequency | Trigger | Estimated Data Size |
|---|---|---|---|
| World Bank Open Data | Monthly (1st, 6 AM) | Airflow schedule | ~2 MB/pull |
| World Bank Documents | Monthly (2nd, 6 AM) | Airflow schedule | ~5 MB/pull |
| World Bank Documents (full text) | Quarterly (Mar/Jun/Sep/Dec 3rd) | Airflow schedule | ~50 MB/pull |
| NSO Vietnam | Monthly (5th, 6 AM) | Airflow schedule | ~1 MB/pull |
| FRED | Weekly (Monday, 6 AM) | Airflow schedule | ~0.5 MB/pull |

**Total estimated Bronze storage growth:** ~10-20 MB/month (very manageable on 512GB SSD)

---

## 7. Data Quality Expectations

| Source | Completeness | Timeliness | Accuracy |
|---|---|---|---|
| World Bank Open Data | High (well-maintained) | 3-6 month lag for latest year | High |
| World Bank Documents | High (automated search) | Real-time for new publications | High |
| NSO Vietnam | Medium (some gaps) | 1-3 month lag after quarter end | Medium-High |
| FRED | High (well-maintained) | Near real-time for most series | High |

### Quality Checks (implemented in dbt tests)

| Check | Applied To | dbt Test |
|---|---|---|
| No null values in key columns | All sources | `not_null` |
| Unique records (no duplicates) | All sources | `unique` on composite key |
| Value within expected range | GDP, CPI | Custom test |
| Date not in future | All sources | Custom test |

---

## 8. Dependency Map

```
┌─────────────────────────────────────────────────────────┐
│                    EXTERNAL DEPENDENCIES                  │
│                                                          │
│  World Bank API v2 ──── No key needed, always available │
│  WDS Documents API ──── No key needed                    │
│  NSO PX-Web API ─────── API key required, unstable      │
│  FRED API ───────────── Free key, highly stable          │
│                                                          │
└─────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│                    INTERNAL DEPENDENCIES                  │
│                                                          │
│  MinIO ───────────── Must be running (target storage)    │
│  Airflow ─────────── Must be running (scheduling)        │
│  Network ─────────── Internet access required            │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

## 9. Secrets Required

| Secret | Source | Where to Get |
|---|---|---|
| `MINIO_ROOT_USER` | Self-generated | Choose during setup |
| `MINIO_ROOT_PASSWORD` | Self-generated | Choose during setup |
| `POSTGRES_PASSWORD` | Self-generated | Choose during setup |
| `GEMINI_API_KEY` | Google AI Studio | https://aistudio.google.com/apikey |
| `FRED_API_KEY` | St. Louis Fed | https://fred.stlouisfed.org/docs/api/api_key.html |
| `NSO_API_KEY` | GSO Portal | Apply via Tổng cục Thống kê (Expand phase) |
