#!/bin/bash
set -e

# Ensure DuckDB working directory exists
mkdir -p "$AIRFLOW_HOME/tmp/duckdb"

# Pre-write the password file so standalone uses our fixed password instead of generating a random one
if [ -n "$AIRFLOW_ADMIN_PASSWORD" ]; then
  echo "{\"admin\": \"$AIRFLOW_ADMIN_PASSWORD\"}" > "$AIRFLOW_HOME/simple_auth_manager_passwords.json.generated"
fi

# Start standalone in background, wait for DB, then seed connections
airflow standalone &
AIRFLOW_PID=$!

# Wait for Airflow DB to be ready
until airflow db check 2>/dev/null; do
  sleep 3
done

# Seed required connections (idempotent)
airflow connections add minio_health \
  --conn-type http \
  --conn-host minio \
  --conn-port 9000 \
  --conn-schema http 2>/dev/null || true

airflow connections add postgres_warehouse \
  --conn-type postgres \
  --conn-host postgres \
  --conn-port 5432 \
  --conn-login "${POSTGRES_USER}" \
  --conn-password "${POSTGRES_PASSWORD}" \
  --conn-schema "${POSTGRES_DB}" 2>/dev/null || true

wait $AIRFLOW_PID
