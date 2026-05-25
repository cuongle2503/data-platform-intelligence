#!/bin/bash
# MinIO Backup Script
set -e

# Load environment variables from .env
DOTENV_PATH="$(dirname "$0")/../../.env"
if [ -f "$DOTENV_PATH" ]; then
    export $(grep -v '^#' "$DOTENV_PATH" | xargs)
else
    echo "Error: .env file not found"
    exit 1
fi

BACKUP_DIR="$(dirname "$0")/../../backups/minio"
mkdir -p "$BACKUP_DIR"
DATE=$(date +%Y%m%d_%H%M)

echo "=== Starting MinIO backup at $DATE ==="

# Using mc (MinIO Client) to mirror to local backup directory
# Assuming mc is configured or we use docker to run it
docker run --rm \
  --network backend_idp-backend \
  -v "$BACKUP_DIR:/backups" \
  minio/mc:RELEASE.2025-02-21T16-00-46Z \
  sh -c "mc alias set myminio http://minio:9000 ${MINIO_ROOT_USER} ${MINIO_ROOT_PASSWORD} && \
         mc mirror myminio/bronze /backups/bronze_$DATE && \
         mc mirror myminio/silver /backups/silver_$DATE"

# Retention: delete backups older than 30 days
find "$BACKUP_DIR" -maxdepth 1 -type d -mtime +30 -exec rm -rf {} +

echo "=== MinIO backup complete ==="
