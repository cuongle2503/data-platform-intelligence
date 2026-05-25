#!/bin/sh
set -e

echo "=== IDP MinIO Bucket Init ==="

# Wait for MinIO to be ready, then set alias
echo "Waiting for MinIO..."
until mc alias set local http://minio:9000 ${MINIO_ROOT_USER} ${MINIO_ROOT_PASSWORD}; do
  echo "  MinIO not ready yet, retrying in 2s..."
  sleep 2
done

echo "MinIO is ready. Creating buckets..."

# Bronze — Raw ingested data (Parquet/CSV)
mc mb local/bronze --ignore-existing
mc anonymous set public local/bronze
echo "  [✓] bronze"

# Silver — Cleaned intermediate data (Parquet)
mc mb local/silver --ignore-existing
mc anonymous set public local/silver
echo "  [✓] silver"

# Artifacts — dbt artifacts, logs, misc
mc mb local/artifacts --ignore-existing
echo "  [✓] artifacts"

echo "=== All buckets created. Init complete. ==="
