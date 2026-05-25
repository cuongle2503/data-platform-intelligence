"""Shared DAG helpers — defaults, health sensors, verification.

Eliminates the duplicated boto3 client creation, env-var reads, and
default_args dicts that were repeated across all 4 DAGs.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import duckdb
from airflow.providers.http.sensors.http import HttpSensor

from idp.core.config import settings
from idp.core.logging import get_logger
from idp.ingestion.services.minio import MinioService

logger = get_logger(__name__)


def default_dag_args(retries: int = 2, retry_delay_minutes: int = 2) -> dict[str, Any]:
    return {
        "owner": "idp",
        "retries": retries,
        "retry_delay": timedelta(minutes=retry_delay_minutes),
        "email_on_failure": False,
    }


def create_minio_health_sensor() -> HttpSensor:
    return HttpSensor(
        task_id="check_minio_health",
        http_conn_id="minio_health",
        endpoint="/minio/health/live",
        response_check=lambda r: r.status_code == 200,
        timeout=30,
        poke_interval=10,
    )


def verify_minio_object(bucket: str, key: str, label: str = "") -> dict[str, Any]:
    """Verify an object exists in MinIO and log its size/age. For use in PythonOperator."""
    with MinioService() as minio:
        resp = minio.head_object(bucket, key)
        size_kb = resp.get("ContentLength", 0) / 1024
        mod = resp.get("LastModified", "?")
        desc = f"{label} — " if label else ""
        logger.info("%ss3://%s/%s — %.1f KB, mod %s", desc, bucket, key, size_kb, mod)
        return resp


def ensure_empty_chunks_parquet(**ctx) -> None:
    """Upload an empty chunks.parquet to MinIO if it doesn't exist yet.

    Ensures dbt model stg_world_bank__docs_chunks won't fail when full-text
    ingestion is skipped (non-quarter months).
    """
    import pyarrow as pa
    import pyarrow.parquet as pq

    bucket = "bronze"
    key = "world_bank_docs/chunks/chunks.parquet"

    with MinioService() as minio:
        try:
            minio.head_object(bucket, key)
            logger.info("chunks.parquet already exists, skipping empty upload")
            return
        except Exception:
            pass

        schema = pa.schema([
            ("chunk_id", pa.string()),
            ("chunk_index", pa.int32()),
            ("text", pa.string()),
            ("doc_id", pa.string()),
            ("title", pa.string()),
            ("display_date", pa.string()),
            ("doc_type", pa.string()),
            ("countries", pa.list_(pa.string())),
            ("topics", pa.list_(pa.string())),
            ("language", pa.string()),
            ("_ingested_at", pa.timestamp("us")),
            ("_source", pa.string()),
        ])
        table = pa.table({f.name: pa.array([], type=f.type) for f in schema}, schema=schema)

        # Write to temp file then upload using MinioService's existing API
        tmp_path = "/tmp/empty_chunks.parquet"
        pq.write_table(table, tmp_path)
        minio.upload_parquet(tmp_path, bucket, key)
        logger.info("Uploaded empty chunks.parquet placeholder")


def ensure_duckdb_secret(db_path: str) -> None:
    """Create persistent S3 secret in DuckDB for dbt external queries.

    Reads credentials from settings (env vars) instead of hardcoding.
    """
    conn = duckdb.connect(db_path)
    try:
        conn.execute("LOAD httpfs;")
    except Exception:
        conn.execute("INSTALL httpfs; LOAD httpfs;")
    try:
        conn.execute(
            f"CREATE PERSISTENT SECRET IF NOT EXISTS minio_s3 "
            f"(TYPE S3, ENDPOINT '{settings.duckdb_s3_endpoint}', "
            f"KEY_ID '{settings.duckdb_s3_access_key}', "
            f"SECRET '{settings.duckdb_s3_secret_key}', "
            f"USE_SSL {str(settings.duckdb_s3_use_ssl).lower()}, "
            f"URL_STYLE '{settings.duckdb_s3_url_style}')"
        )
        logger.info("DuckDB S3 secret created (endpoint: %s)", settings.duckdb_s3_endpoint)
    except Exception:
        logger.debug("DuckDB secret already exists (expected on re-runs)")
    conn.close()
