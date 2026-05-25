# Phase 2: Ingestion — Manual First

> **Status: ✅ Done (verified 2026-05-20) | Duration: ~3 ngày | Rule: CLI only, chưa Airflow**

---

## Mục tiêu

2 Python connector chạy từ CLI → kéo data từ World Bank API → ghi Parquet → upload lên MinIO Bronze. Mỗi connector có thể chạy lại nhiều lần không lỗi (idempotent).

---

## 2.1 Shared infrastructure (0.25 ngày)

- [x] 2.1.1 Tạo `ingestion/shared/config.py`
  - Load env vars: `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`, `MINIO_ENDPOINT`, `MINIO_CONNECTOR_ENDPOINT`
  - Fallback logic: nếu `MINIO_ENDPOINT=http://minio:9000` → connector host dùng `http://127.0.0.1:9000`
  - Parse `MINIO_CONNECTOR_ENDPOINT` nếu được set

- [x] 2.1.2 Tạo `ingestion/shared/minio_client.py`
  - Hàm `get_minio_client()` → trả về boto3 client với credentials từ config
  - Hàm `upload_parquet(local_path, bucket, key)` → upload + verify
  - Hàm `list_objects(bucket, prefix)` → kiểm tra objects đã tồn tại

- [x] 2.1.3 Cài dependencies
  - `pip install requests pandas pyarrow boto3 wbgapi`
  - Không cần pdfplumber: dùng World Bank server-side text extraction (`/text/` endpoint)
  - Freeze vào `requirements.txt`

---

## 2.2 World Bank Open Data connector (0.5 ngày)

- [x] 2.2.1 Tạo `ingestion/connectors/world_bank/client.py`
  - Hàm `fetch_indicators(country_codes, indicator_codes, start_year, end_year)`
    - Gọi `wbgapi.data.DataFrame(series=indicators, economy=countries, time=range(start, end+1))`
    - Transform về flat table: country_code, country_name, indicator_code, indicator_name, year, value
    - Thêm `_ingested_at` = `datetime.now(timezone.utc)`
    - Thêm `_source` = `"world_bank"`
    - Trả về pandas DataFrame

- [x] 2.2.2 Tạo `ingestion/connectors/world_bank/main.py`
  - argparse: `--start-year`, `--end-year`, `--countries` (default: 10 nước), `--indicators` (default: 32 indicators)
  - Gọi `client.fetch_indicators()`
  - Ghi DataFrame → local Parquet: `tmp/world_bank/year={YYYY}/data.parquet`
  - Upload lên MinIO: `s3://bronze/world_bank/indicators/year={YYYY}/data.parquet`
  - In summary: row count, file size, upload path

- [x] 2.2.3 Test connector
  - `python3 -m ingestion.connectors.world_bank.main --start-year 2024 --end-year 2024`
  - Verify: MinIO console có object `bronze/world_bank/indicators/year=2024/data.parquet` ✓ (9190 bytes, 239 rows, 27 indicators × 10 countries)
  - Verify: đọc lại Parquet, check row count > 0, columns đúng schema ✓ (8 columns đúng spec data-model.md)

- [x] 2.2.4 Test idempotency
  - Chạy lại cùng command → không lỗi, file bị overwrite đúng cách (LastModified updated, size không đổi)

---

## 2.3 World Bank Documents connector (1 ngày)

- [x] 2.3.1 Tạo `ingestion/connectors/world_bank_docs/wds_client.py`
  - Hàm `search_documents(queries)` → gọi `https://search.worldbank.org/api/v2/wds`
    - 5 queries định sẵn (xem `source-catalog.md` section 3.2)
    - Gộp kết quả, deduplicate theo `doc_id`
    - Trả về list of dict (metadata)

- [x] 2.3.2 Tạo `ingestion/connectors/world_bank_docs/main.py` (metadata mode)
  - argparse: `--full-text` (flag, default False) — dùng text endpoint thay vì tải PDF
  - Gọi `wds_client.search_documents()`
  - Transform → DataFrame với schema metadata (doc_id, title, abstract, display_date, doc_type, pdf_url, countries, topics, language)
  - Thêm `_ingested_at`, `_source = "world_bank_docs"`
  - Ghi local Parquet: `tmp/world_bank_docs/metadata/documents.parquet`
  - Upload MinIO: `s3://bronze/world_bank_docs/metadata/documents.parquet`

- [x] 2.3.3 Test metadata mode
  - `python3 -m ingestion.connectors.world_bank_docs.main`
  - Verify MinIO có object, row count > 0, columns đúng ✓ (101 docs, 11 columns đúng spec data-model.md, 100/101 có pdf_url)

---

## 2.4 Text extraction + chunking (1 ngày)

- [x] 2.4.1 Tạo `ingestion/connectors/world_bank_docs/text_loader.py`
  - Hàm `fetch_document_text(pdf_url, session=None)` → gọi World Bank `/text/` endpoint lấy server-extracted text
    - Chuyển `/pdf/...pdf` → `/text/...txt`, giữ nguyên HTTP headers (browser-like)
    - Retry 4 lần với exponential backoff (`2s, 4s, 6s`) cho `403/429/502/503/504` — Cloudflare WAF chặn intermittent
    - Server-side extraction cho text chất lượng hơn PDF parsing (~70% nhiều chars hơn, không mất whitespace)
  - Không cần pdfplumber hay PyPDF2 vì dùng server-side text extraction

- [x] 2.4.2 Tạo `ingestion/connectors/world_bank_docs/chunker.py`
  - Hàm `chunk_text(text, chunk_size=1500, overlap=200, doc_id="")`
    - Split paragraph qua `\n\s*\n+` (regex), không phải `\n` đơn
    - Force-split paragraph quá dài: fallback sentence boundary → fixed-width chars
    - Overlap an toàn: chỉ carry tail nếu `tail + para` ≤ chunk_size
    - `chunk_id` = MD5(`doc_id\x00index\x00text`) → unique kể cả khi 2 docs có cùng template (Procurement Plan, etc.)
  - Trả về list of dict: chunk_id, chunk_index, text
  - Unit-tested: empty / short / long single paragraph / repeated paragraph / cross-doc collision — tất cả pass

- [x] 2.4.3 Tích hợp vào `main.py` (full-text mode)
  - Khi `--full-text`: sau metadata → fetch text từ `/text/` endpoint → chunk → ghi DataFrame chunks
  - Schema chunks (xem `data-model.md` section 3.3)
  - Ghi local: `tmp/world_bank_docs/chunks/chunks.parquet`
  - Upload MinIO: `s3://bronze/world_bank_docs/chunks/chunks.parquet`
  - Verified: schema 11 columns đúng spec, 1573 chunks từ 44 docs upload thành công

- [x] 2.4.4 Test full-text mode
  - `python3 -m ingestion.connectors.world_bank_docs.main --full-text`
  - Verify MinIO có `chunks/chunks.parquet` ✓
  - Coverage: **94/101 docs (93%)** sau retry + `/text/` fallback (vs 26% baseline)
  - 4843 chunks, **100% unique chunk_id** (hash bao gồm `doc_id + index + text`)
  - 100% chunks ≤ 1500 chars (range 203–1500, mean 1376)
  - Idempotent: rerun overwrite cùng key

---

## 2.5 Runbook (0.25 ngày)

- [x] 2.5.1 Xác nhận các lệnh trong `docs/ingestion-manual-runbook.md` khớp với code thực tế
- [x] 2.5.2 Test flow đầy đủ: MinIO start → 2 connector → MinIO stop (theo runbook section 4)
- [x] 2.5.3 Verify output sizes (actual on bronze 2026-05-20):
  - `world_bank/indicators/` — 10 files, 94.1 KB total (~9.4 KB/year)
  - `world_bank_docs/metadata/` — 1 file, 35.8 KB (101 docs)
  - `world_bank_docs/chunks/` — 1 file, 590.7 KB (1034 chunks from 26 docs)

---

## Tổng: 20 checklist items | ~3 ngày

**Next: [Phase 3 — Transformation](03-transformation.md)**
