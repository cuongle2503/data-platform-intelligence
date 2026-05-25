#!/bin/bash
# PostgreSQL Backup Script
set -e

BACKUP_DIR="$(dirname "$0")/../../backups"
mkdir -p "$BACKUP_DIR"
DATE=$(date +%Y%m%d_%H%M)

echo "=== Starting PostgreSQL backup at $DATE ==="

# Get container name
CONTAINER=$(docker ps --filter "name=postgres" --format "{{.Names}}" | head -n 1)
if [ -z "$CONTAINER" ]; then
    echo "Error: Postgres container not found"
    exit 1
fi

echo "=== Starting PostgreSQL backup from $CONTAINER at $DATE ==="

# Backup idp_warehouse via docker
docker exec "$CONTAINER" pg_dump -U admin -d idp_warehouse --format=custom > "$BACKUP_DIR/idp_warehouse_$DATE.dump"
SIZE=$(stat --printf="%s" "$BACKUP_DIR/idp_warehouse_$DATE.dump")
echo "idp_warehouse backup: $SIZE bytes"

# Backup airflow_db via docker
docker exec "$CONTAINER" pg_dump -U admin -d airflow_db --format=custom > "$BACKUP_DIR/airflow_db_$DATE.dump"
SIZE=$(stat --printf="%s" "$BACKUP_DIR/airflow_db_$DATE.dump")
echo "airflow_db backup: $SIZE bytes"

# Retention: delete backups older than 7 days
find "$BACKUP_DIR" -name "*.dump" -mtime +7 -delete

echo "=== Backup complete. Files in $BACKUP_DIR ==="
ls -lh "$BACKUP_DIR"
