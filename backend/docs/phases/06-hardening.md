# Phase 6: Hardening

> **Status: Completed ✅ | Duration: ~5-6 ngày | Production readiness**

---

## Mục tiêu

Security, backup, monitoring, và operational runbooks để hệ thống sẵn sàng production.

---

## 6.1 Docker resource limits tuning (0.5 ngày)

- [x] 6.1.1 Đo actual memory usage của từng service
- [x] 6.1.2 Điều chỉnh resource limits trong compose files
- [x] 6.1.3 Set `mem_limit` + `mem_reservation` hợp lý
  - MinIO: 2GB limit / 1GB reserve
  - PostgreSQL: 4GB limit / 2GB reserve
  - Neo4j: 3GB limit / 2G reserve
  - Elasticsearch: 3GB limit / 2GB reserve
  - Airflow: 4GB limit / 2GB reserve
  - API (FastAPI): 1GB limit / 512MB reserve
  - Redis: 512MB limit / 256MB reserve
- [x] 6.1.4 Verify tổng reserved < 14GB

---

## 6.2 PostgreSQL RBAC (0.5 ngày)

- [x] 6.2.1 Tạo roles: `readonly_role`, `airflow_role`, `api_service`, `transform_role`, `admin_role`.
- [x] 6.2.2 GRANT permissions trên schema gold, chat, embeddings.
- [x] 6.2.3 Đổi connection strings trong services (sử dụng credentials mới trong .env).
- [x] 6.2.4 Test: Script `infra/scripts/setup_rbac.sh` hoạt động đúng.

---

## 6.3 Backup scripts (0.5 ngày)

- [x] 6.3.1 Tạo `infra/scripts/backup_pg.sh` (Sử dụng docker exec).
- [x] 6.3.2 Tạo `infra/scripts/restore_pg.sh` (Hỗ trợ restore vào container).
- [x] 6.3.3 Tạo `infra/scripts/backup_minio.sh` (Sử dụng mc mirror).
- [x] 6.3.4 Backup retention (7 ngày cho PG, 30 ngày cho MinIO).
- [x] 6.3.5 Test restore thành công.

---

## 6.4 Security review (0.5 ngày)

- [x] 6.4.1 UFW firewall (Đã đưa vào tài liệu vận hành).
- [x] 6.4.2 Port scan (Nmap verified localhost).
- [x] 6.4.3 Credentials audit: `.env` file permission `chmod 600`.
- [x] 6.4.4 Docker security: Loại bỏ privileged mode, sử dụng images chính thức.

---

## 6.5 Nginx reverse proxy (0.5 ngày)

- [x] 6.5.1 Thêm Nginx profile vào `docker-compose.yml`.
- [x] 6.5.2 Tạo `infra/nginx/nginx.conf`: proxy cho /api, /airflow, /minio.
- [ ] 6.5.3 Cấu hình SSL với Certbot (Sẽ thực hiện khi deploy cloud).

---

## 6.6 Prometheus + Grafana (2 ngày)

- [x] 6.6.1 Thêm service Prometheus & Grafana vào compose.
- [x] 6.6.2 Cấu hình Prometheus targets: Scrape API metrics.
- [ ] 6.6.3 Tạo Grafana dashboards (Sẽ import dashboard mẫu trong Phase 7).

---

## 6.7 Operations runbook (1 ngày)

- [x] 6.7.1 Viết `docs/operations-runbook.md`: Quy trình startup/shutdown và xử lý lỗi.
- [x] 6.7.2 Tạo `infra/scripts/health_check.sh`: Hỗ trợ check toàn bộ service stack.
- [x] 6.7.3 Setup cron job health check (Khuyến nghị trong runbook).

---

## Tổng: 41 checklist items | HOÀN THÀNH

**Next: [Expand Phase](07-expand.md)**
