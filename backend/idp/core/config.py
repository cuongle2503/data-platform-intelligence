"""Single entry point for all configuration. Loads from .env via Pydantic BaseSettings.

Usage:
    from idp.core.config import settings
    print(settings.minio_root_user)
"""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """All environment-driven configuration. Values read from .env file."""

    model_config = SettingsConfigDict(
        env_file=[".env", str(PROJECT_ROOT / ".env")],
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # -- MinIO / S3 --
    minio_root_user: str = Field(validation_alias="MINIO_ROOT_USER")
    minio_root_password: str = Field(validation_alias="MINIO_ROOT_PASSWORD")
    minio_endpoint: str = Field(
        default="http://minio:9000", validation_alias="MINIO_ENDPOINT"
    )
    minio_connector_endpoint: str = Field(
        default="http://127.0.0.1:9000", validation_alias="MINIO_CONNECTOR_ENDPOINT"
    )

    # -- PostgreSQL --
    postgres_host: str = Field(default="postgres", validation_alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, validation_alias="POSTGRES_PORT")
    postgres_user: str = Field(validation_alias="POSTGRES_USER")
    postgres_password: str = Field(validation_alias="POSTGRES_PASSWORD")
    postgres_db: str = Field(
        default="idp_warehouse", validation_alias="POSTGRES_DB"
    )

    # -- Airflow --
    airflow_db_conn: str = Field(validation_alias="AIRFLOW__DATABASE__SQL_ALCHEMY_CONN")
    airflow_fernet_key: str = Field(validation_alias="AIRFLOW__CORE__FERNET_KEY")
    airflow_api_secret_key: str = Field(
        validation_alias="AIRFLOW_WEBSERVER_SECRET_KEY"
    )

    # -- DuckDB (dbt profiles, S3 access) --
    duckdb_s3_endpoint: str = Field(
        default="minio:9000", validation_alias="DUCKDB_S3_ENDPOINT"
    )
    duckdb_s3_access_key: str = Field(validation_alias="DUCKDB_S3_ACCESS_KEY")
    duckdb_s3_secret_key: str = Field(validation_alias="DUCKDB_S3_SECRET_KEY")
    duckdb_s3_use_ssl: bool = Field(
        default=False, validation_alias="DUCKDB_S3_USE_SSL"
    )
    duckdb_s3_url_style: str = Field(
        default="path", validation_alias="DUCKDB_S3_URL_STYLE"
    )

    # -- Paths --
    tmp_dir: Path = PROJECT_ROOT / "tmp"
    duckdb_path: Path = PROJECT_ROOT / "tmp" / "duckdb" / "idp.db"
    dbt_dir: Path = PROJECT_ROOT / "transform" / "dbt"

    @property
    def postgres_conn_str(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def minio_s3_config(self) -> dict[str, object]:
        return {
            "endpoint_url": self.minio_endpoint,
            "aws_access_key_id": self.minio_root_user,
            "aws_secret_access_key": self.minio_root_password,
        }


# Singleton — every module imports this
settings = Settings()
