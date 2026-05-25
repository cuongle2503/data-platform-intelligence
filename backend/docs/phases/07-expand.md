# Expand Phase — After Lean is Validated

> **Status: On Hold | Trigger-based, không theo calendar | Deploy khi Lean (Phase 0-6) ổn định**

---

## E.1 Thêm data sources (trigger: core pipeline stable)

- [ ] E.1.1 NSO Vietnam connector (PX-Web API → Parquet → MinIO)
  - Tạo `ingestion/connectors/nso/`: client.py + main.py
  - DAG `ingest_nso` (monthly)
  - Staging model `stg_nso__*` trong dbt
  - **Rủi ro:** PX-Web API không ổn định, format có thể thay đổi giữa các kỳ
  - ~2 ngày

- [ ] E.1.2 FRED connector (fredapi → Parquet)
  - Tạo `ingestion/connectors/fred/`: client.py + main.py
  - Cần API key (free tier từ St. Louis Fed)
  - DAG `ingest_fred` (weekly)
  - ~1 ngày

---

## E.2 Google Cloud Platform (trigger: production readiness)

- [ ] E.2.1 GCS backup
  - `gsutil rsync` hoặc `mc mirror` backup files lên GCS
  - Lifecycle policy: auto-delete objects > 90 days
  - ~1 ngày

- [ ] E.2.2 BigQuery integration
  - Export Gold data → BigQuery tables
  - dbt-bigquery adapter cho heavy analytics queries
  - Partition + cluster settings
  - ~3 ngày

- [ ] E.2.3 Google Cloud IAM + Secret Manager
  - Service account với quyền tối thiểu
  - API keys migrate từ `.env` → Secret Manager
  - ~1 ngày

---

## E.3 BI & Presentation (trigger: external stakeholders cần dashboard)

- [ ] E.3.1 Looker Studio dashboards
  - Connect Looker Studio → PostgreSQL qua JDBC
  - Dashboard templates: economic overview, country comparison
  - ~4 ngày

---

## E.4 Advanced Orchestration (trigger: DAGs chạy chậm)

- [ ] E.4.1 CeleryExecutor migration
  - Redis broker + Celery workers (2+ workers)
  - Phân phối tasks: ingestion workers, transform workers riêng
  - ~2 ngày

- [ ] E.4.2 DAG versioning + rollback
  - Serialized DAGs trong Git
  - Auto-test DAG import trước khi deploy
  - ~1 ngày

---

## E.5 Machine Learning (trigger: cần forecasting)

- [ ] E.5.1 XGBoost economic forecasting
  - Train model trên historical indicators
  - Features: lag indicators, regional context, global trends
  - Model registry trong MLflow
  - ~5 ngày

- [ ] E.5.2 Prophet time series baseline
  - Quick forecast cho GDP, CPI
  - So sánh accuracy với XGBoost
  - ~2 ngày

- [ ] E.5.3 Econometric models (statsmodels)
  - ARIMA, VAR cho causal analysis
  - ~3 ngày

- [ ] E.5.4 MLOps pipeline
  - MLflow experiment tracking
  - Evidently AI drift detection (data + concept drift)
  - SHAP explainability reports
  - ~4 ngày

---

## E.6 Agentic AI (trigger: basic RAG không đủ cho complex queries)

- [ ] E.6.1 LangGraph agent setup
  - Tool definitions: query_data, search_docs, compare_countries, fetch_indicator_def
  - Multi-step planning: decompose complex query → execute tools → synthesize
  - ~8 ngày

- [ ] E.6.2 LlamaIndex advanced RAG
  - Hybrid search (vector + keyword + graph)
  - Re-ranking với cross-encoder
  - ~3 ngày

---

## E.7 CI/CD (trigger: team collaboration)

- [ ] E.7.1 GitHub Actions pipeline
  - Lint: ruff, black, mypy
  - Test: pytest (connector tests, dbt tests)
  - Build: Docker image build + push to registry
  - ~2 ngày

- [ ] E.7.2 Pre-commit hooks
  - ruff format + check, black, isort
  - `.pre-commit-config.yaml`
  - ~0.5 ngày

---

## E.8 External access hardening (trigger: internet exposure)

- [ ] E.8.1 SSL certificates
  - Let's Encrypt qua Certbot + Nginx
  - Auto-renew cron
  - ~1 ngày

- [ ] E.8.2 Cloudflare Tunnel / Tailscale
  - Zero-trust access, không mở port
  - ~1 ngày

---

## Notes

- Tổng expand: **~45 ngày** nếu làm hết, nhưng chọn lọc theo nhu cầu thực tế
- Mỗi item được trigger bởi business need, không phải deadline
- Không cần làm hết — đây là menu, không phải checklist bắt buộc
