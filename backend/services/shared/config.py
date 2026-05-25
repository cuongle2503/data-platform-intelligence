from __future__ import annotations

from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]  # backend/

class Settings(BaseSettings):
    """Configuration for FastAPI and AI services. Values read from .env file."""
    project_root: Path = PROJECT_ROOT

    model_config = SettingsConfigDict(
        env_file=[".env", str(PROJECT_ROOT / ".env")],
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # -- General --
    environment: str = Field(default="development", validation_alias="ENVIRONMENT")
    allowed_origins: str = Field(default="http://localhost:3000,http://127.0.0.1:3000", validation_alias="ALLOWED_ORIGINS")

    # -- PostgreSQL --
    postgres_host: str = Field(default="127.0.0.1", validation_alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5433, validation_alias="POSTGRES_PORT")
    postgres_user: str = Field(validation_alias="POSTGRES_USER")
    postgres_password: str = Field(validation_alias="POSTGRES_PASSWORD")
    postgres_db: str = Field(default="idp_warehouse", validation_alias="POSTGRES_DB")

    # -- Neo4j --
    neo4j_uri: str = Field(default="bolt://localhost:7687", validation_alias="NEO4J_URI")
    neo4j_user: str = Field(validation_alias="NEO4J_USER")
    neo4j_password: str = Field(validation_alias="NEO4J_PASSWORD")

    # -- Elasticsearch --
    es_host: str = Field(default="http://localhost:9200", validation_alias="ES_HOST")

    # -- Redis & Celery --
    redis_url: str = Field(default="redis://localhost:6379/0", validation_alias="REDIS_URL")

    # -- LLM API --
    gemini_api_key: str | None = Field(default=None, validation_alias="GEMINI_API_KEY")

    database_url: str = Field(default="", validation_alias="DATABASE_URL")

    def model_post_init(self, __context):
        if not self.database_url:
            object.__setattr__(self, 'database_url',
                f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
            )

settings = Settings()
