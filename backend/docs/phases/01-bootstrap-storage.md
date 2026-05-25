# Phase 1: Bootstrap Storage

> **Status: ✅ Done (verified 2026-05-20) | Duration: ~1.5-2 ngày | Server: Ubuntu 22.04, 16GB/512GB**

---

## Mục tiêu

Chạy MinIO container trên server, tạo xong 3 bucket `bronze`, `silver`, `artifacts`, xác nhận upload/read hoạt động.

> **Note:** Hiện tại chỉ `bronze` được sử dụng (ingestion ghi Parquet vào đây). `silver` và `artifacts` là bucket dự phòng cho các phase sau — Silver layer hiện tại là DuckDB views, chưa ghi file ra MinIO.

---

## 1.1 Tạo bootstrap compose cho MinIO (0.5 ngày)

- [x] 1.1.1 create unified `docker-compose.yml`
  - service `minio`:
    - image `minio/minio:latest`
    - command `server /data --console-address :9001`
    - port `9000:9000` (API), `9001:9001` (console)
    - volume `minio_data:/data`
    - env `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD` từ `.env`
    - healthcheck `curl http://localhost:9000/minio/health/live`
    - restart `unless-stopped`
    - network `idp-backend`
    - resource limit: 2GB mem, 1 CPU
  - service `minio-init` (one-shot):
    - image `minio/mc:latest`
    - depends_on `minio` (service_healthy)
    - entrypoint `/bin/sh /scripts/minio-init.sh`
    - volume mount `./infra/scripts/minio-init.sh:/scripts/minio-init.sh:ro`
    - env từ `.env`
    - network `idp-backend`
  - network `idp-backend` (bridge)
  - volume `minio_data`

- [x] 1.1.2 Tạo `infra/scripts/minio-init.sh`
  - loop `until mc alias set local http://minio:9000 $MINIO_ROOT_USER $MINIO_ROOT_PASSWORD`
  - `mc mb local/bronze --ignore-existing`
  - `mc mb local/silver --ignore-existing`
  - `mc mb local/artifacts --ignore-existing`
  - echo success message
  - set -e ở đầu script

---

## 1.2 Cấu hình `.env` + secrets (0.5 ngày)

- [x] 1.2.1 Tạo `.env.example` template
  - `COMPOSE_PROJECT_NAME=idp`
  - `TZ=Asia/Ho_Chi_Minh`
  - `MINIO_ROOT_USER=minio_admin`
  - `MINIO_ROOT_PASSWORD=CHANGE_ME`
  - `MINIO_ENDPOINT=http://minio:9000`

- [x] 1.2.2 Copy `.env.example` → `.env`
  - Generate `MINIO_ROOT_PASSWORD` (openssl rand -hex 32)
  - Giữ nguyên các giá trị khác

- [x] 1.2.3 Xác nhận `.env` trong `.gitignore`
  - Không commit `.env` lên git ✓ (`.gitignore` cập nhật: bỏ rule sai `docs/`, thêm `.env`, `tmp/`, `__pycache__/`, `*.pyc`, `.venv/`)

- [x] 1.2.4 Test lệnh compose
  - `docker compose --env-file .env config` không lỗi

---

## 1.3 Khởi động & validate MinIO (0.25 ngày)

- [x] 1.3.1 Start stack
  - `docker compose --env-file .env up -d`
  - `docker compose ps` — cả 2 service running (minio-init đã exit 0)

- [x] 1.3.2 Health check MinIO API
  - `curl -fsS http://127.0.0.1:9000/minio/health/live` → 200 OK

- [x] 1.3.3 Mở MinIO Console
  - `http://<server-ip>:9001` — login bằng MINIO_ROOT_USER/PASSWORD
  - Xác nhận thấy 3 buckets: `bronze`, `silver`, `artifacts` (verified qua `list_buckets()`)

---

## 1.4 Smoke test upload/read (0.25 ngày)

- [x] 1.4.1 Tạo file test Parquet bằng Python
  - `python3 -c "import pandas as pd; pd.DataFrame({'test': [1,2,3]}).to_parquet('/tmp/test.parquet')"`

- [x] 1.4.2 Upload lên MinIO bằng boto3
  - `python3 -c "..."` — upload `test.parquet` → `s3://bronze/manual-smoke/ingest_date=$(date +%Y-%m-%d)/test.parquet`

- [x] 1.4.3 Download & verify
  - Download lại file từ MinIO, đọc bằng pandas, so sánh row count (3 rows, equals OK)

- [ ] 1.4.4 Upload qua MinIO Console
  - Upload file trực tiếp qua web UI, xác nhận hiển thị trong bucket
  - **Skipped**: cần thao tác thủ công qua browser; boto3 round-trip đã chứng minh API path

---

## 1.5 Document workflow (0.25 ngày)

- [x] 1.5.1 Viết startup command vào `docs/environment-config.md` (đã có section 8.1)

- [x] 1.5.2 Ghi lại các lệnh thường dùng
  - Start: `docker compose --env-file .env up -d`
  - Stop: `docker compose --env-file .env down`
  - Logs: `docker compose --env-file .env logs -f minio`
  - Status: `docker compose --env-file .env ps`
  - Health: `curl -fsS http://127.0.0.1:9000/minio/health/live`

- [x] 1.5.3 Xác nhận volume persistence
  - `docker compose down && docker compose up -d` → buckets vẫn còn, data không mất
  - Verified: container chạy 21h trước, restart vẫn giữ buckets `bronze/silver/artifacts`

---

## Tổng: 14 checklist items | ~1.5-2 ngày

**Next: [Phase 2 — Ingestion](02-ingestion.md)**
