#!/bin/bash
# PostgreSQL Restore Script
set -e

if [ -z "$1" ]; then
    echo "Usage: $0 <backup-file.dump> [database]"
    exit 1
fi

BACKUP_FILE="$1"
DB_NAME="${2:-idp_warehouse}"

if [ ! -f "$BACKUP_FILE" ]; then
    echo "Backup file not found: $BACKUP_FILE"
    exit 1
fi

CONTAINER=$(docker ps --filter "name=postgres" --format "{{.Names}}" | head -n 1)
if [ -z "$CONTAINER" ]; then
    echo "Error: Postgres container not found"
    exit 1
fi

echo "=== Restoring $BACKUP_FILE to database $DB_NAME in $CONTAINER ==="
# Use docker exec to restore. Need to mount or pipe.
cat "$BACKUP_FILE" | docker exec -i "$CONTAINER" pg_restore -U admin -d "$DB_NAME" --clean --if-exists

echo "=== Restore complete. Verifying row counts ==="
docker exec -i "$CONTAINER" psql -U admin -d "$DB_NAME" -c "
SELECT 'gold.dim_countries' AS table_name, COUNT(*) FROM gold.dim_countries
UNION ALL SELECT 'gold.dim_indicators', COUNT(*) FROM gold.dim_indicators
UNION ALL SELECT 'gold.fact_economic_indicators', COUNT(*) FROM gold.fact_economic_indicators;
"
