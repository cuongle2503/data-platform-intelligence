"""MinioService — wraps boto3 S3 client for MinIO operations."""

from __future__ import annotations

from typing import Any

import boto3
from botocore.config import Config

from idp.core.config import settings
from idp.core.logging import get_logger

logger = get_logger(__name__)


class MinioService:
    """Lazy-init boto3 client for MinIO. Use as context manager or standalone."""

    def __init__(self) -> None:
        self._client: Any = None

    @property
    def client(self) -> Any:
        if self._client is None:
            self._client = boto3.client(
                "s3",
                endpoint_url=settings.minio_connector_endpoint,
                aws_access_key_id=settings.minio_root_user,
                aws_secret_access_key=settings.minio_root_password,
                config=Config(signature_version="s3v4"),
                region_name="us-east-1",
            )
            logger.info("MinioService client created for %s", settings.minio_connector_endpoint)
        return self._client

    def upload_parquet(self, local_path: str, bucket: str, key: str) -> None:
        """Upload a local file to MinIO."""
        self.client.upload_file(local_path, bucket, key)
        logger.info("Uploaded %s → s3://%s/%s", local_path, bucket, key)

    def head_object(self, bucket: str, key: str) -> dict[str, Any]:
        """Return object metadata or raise on missing object."""
        resp = self.client.head_object(Bucket=bucket, Key=key)
        size_kb = resp.get("ContentLength", 0) / 1024
        mod = resp.get("LastModified", "?")
        logger.info("Object s3://%s/%s — %.1f KB, mod %s", bucket, key, size_kb, mod)
        return resp

    def list_objects(self, bucket: str, prefix: str) -> list[dict[str, Any]]:
        """Paginate and list objects under a prefix."""
        paginator = self.client.get_paginator("list_objects_v2")
        result: list[dict[str, Any]] = []
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                result.append({
                    "Key": obj["Key"],
                    "Size": obj["Size"],
                    "LastModified": obj["LastModified"],
                })
        return result

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self) -> MinioService:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
