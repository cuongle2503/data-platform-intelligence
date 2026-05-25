"""Abstract base class for all data connectors using the Template Method pattern."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import pandas as pd

from idp.core.logging import get_logger
from idp.ingestion.services.minio import MinioService


class AbstractConnector(ABC):
    """Template Method: extract() → transform() → load().

    Subclasses implement extract() and transform(). The load() method
    and run() orchestration are shared.
    """

    def __init__(self, minio: MinioService | None = None) -> None:
        self.minio = minio or MinioService()
        self.logger = get_logger(self.__class__.__name__)

    @abstractmethod
    def extract(self, **kwargs: object) -> Any:
        """Fetch raw data from source. Return type defined by subclass."""
        ...

    @abstractmethod
    def transform(self, raw: Any) -> pd.DataFrame:
        """Transform raw data into a DataFrame ready for storage."""
        ...

    def load(self, df: pd.DataFrame, local_path: Path, bucket: str, key: str) -> None:
        """Write DataFrame to local Parquet and upload to MinIO."""
        local_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(local_path, index=False)
        self.minio.upload_parquet(str(local_path), bucket, key)

    def run(self, **kwargs: object) -> None:
        """Template method: full ETL pipeline."""
        self.logger.info("Starting %s", self.__class__.__name__)
        raw = self.extract(**kwargs)
        df = self.transform(raw)
        if df.empty:
            self.logger.warning("No data — skipping load")
            return
        self._load_multiple(df, **kwargs)

    @abstractmethod
    def _load_multiple(self, df: pd.DataFrame, **kwargs: object) -> None:
        """Subclass-specific partition logic — required."""

    def close(self) -> None:
        self.minio.close()
