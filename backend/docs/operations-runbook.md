# IDP Operations Runbook

Hệ thống Intelligent Data Platform (IDP) được vận hành dựa trên kiến trúc Medallion kết hợp Graph-Augmented RAG.

## 1. Startup & Shutdown

### Khởi động môi trường Production
Sử dụng docker-compose mặc định (không mount code, không reload):
```bash
docker compose up -d
```
Thứ tự tự động: `postgres` -> `minio` -> `elasticsearch` -> `neo4j` -> `redis` -> `airflow` -> `api`.

### Khởi động môi trường Development
Sử dụng thêm file override để bật hot-reload và bind mount source code:
```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

### Local Development (Không Docker cho API)
Cài đặt môi trường và dependencies:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```
Chạy FastAPI:
```bash
uvicorn services.api.main:app --host 0.0.0.0 --port 8000 --reload
```

## 2. Testing
Test suite yêu cầu cài đặt package local và dependencies.
```bash
pip install -e .
pytest -q
```
*Lưu ý: API health và metrics endpoints được thiết kế fail-fast. Database phải kết nối được thì ứng dụng mới khởi động. AI features (Gemini/Neo4j) được khởi tạo lazy, nên test `/health` sẽ không fail nếu thiếu API key.*

## 2. Health & Monitoring

### Kiểm tra sức khỏe hệ thống
Chạy script:
```bash
./infra/scripts/health_check.sh
```

### Metrics & Dashboard
- **Prometheus**: http://localhost:8000/metrics (FastAPI)
- **Grafana**: http://localhost:3000 (Tích hợp trong Phase 6)

## 3. Database Operations

### Phân quyền (RBAC)
Cấu hình roles cho service:
```bash
./infra/scripts/setup_rbac.sh
```

### Sao lưu (Backup)
```bash
./infra/scripts/backup_pg.sh
```
File sao lưu được lưu tại thư mục `backups/` ở gốc dự án.

### Phục hồi (Restore)
```bash
./infra/scripts/restore_pg.sh backups/idp_warehouse_YYYYMMDD_HHMM.dump
```

## 4. Các sự cố thường gặp (Troubleshooting)

| Sự cố | Cách xử lý |
|-------|------------|
| MinIO Unhealthy | `docker compose restart minio` |
| RAG không có dữ liệu số | Kiểm tra `gold.fact_economic_indicators` và chạy Airflow DAG `export_gold_to_postgres` |
| Neo4j OOM | Tăng `dbms.memory.heap.max_size` trong config |
| Rate limit 429 | Đợi 1 phút hoặc điều chỉnh cấu hình trong `services/api/main.py` |

---
*Người phụ trách: @cuongle2503*
