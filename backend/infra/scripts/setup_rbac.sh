#!/bin/bash
# PostgreSQL Role-Based Access Control Setup for IDP
set -e

# Load environment variables from .env
DOTENV_PATH="$(dirname "$0")/../../.env"
if [ -f "$DOTENV_PATH" ]; then
    echo "Loading environment variables from $DOTENV_PATH"
    # Export variables for the script to use
    export $(grep -v '^#' "$DOTENV_PATH" | xargs)
else
    echo "Error: .env file not found at $DOTENV_PATH"
    exit 1
fi

echo "=== Setting up PostgreSQL RBAC ==="

# Get container name
CONTAINER=$(docker ps --filter "name=postgres" --format "{{.Names}}" | head -n 1)
if [ -z "$CONTAINER" ]; then
    echo "Error: Postgres container not found"
    exit 1
fi

echo "=== Setting up PostgreSQL RBAC in $CONTAINER ==="

# Run as superuser (admin)
docker exec -i "$CONTAINER" psql -U admin -d idp_warehouse <<SQL
-- 1. Create roles
DO \$\$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'readonly_role') THEN
        CREATE ROLE readonly_role NOLOGIN;
    END IF;
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'api_service') THEN
        CREATE ROLE api_service LOGIN PASSWORD '${API_SERVICE_PASSWORD}';
    END IF;
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'airflow_role') THEN
        CREATE ROLE airflow_role LOGIN PASSWORD '${AIRFLOW_ROLE_PASSWORD}';
    END IF;
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'transform_role') THEN
        CREATE ROLE transform_role LOGIN PASSWORD '${TRANSFORM_ROLE_PASSWORD}';
    END IF;
END
\$\$;

-- 2. Grant schema usage
GRANT USAGE ON SCHEMA gold TO readonly_role, api_service, transform_role, airflow_role;
GRANT USAGE ON SCHEMA chat TO api_service, airflow_role;
GRANT USAGE ON SCHEMA embeddings TO api_service, airflow_role;

-- 3. Grant readonly access
GRANT SELECT ON ALL TABLES IN SCHEMA gold TO readonly_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA gold GRANT SELECT ON TABLES TO readonly_role;

GRANT SELECT ON ALL TABLES IN SCHEMA gold TO api_service;
ALTER DEFAULT PRIVILEGES IN SCHEMA gold GRANT SELECT ON TABLES TO api_service;

-- 4. Grant read+write to chat schema (for API to save messages)
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA chat TO api_service;
ALTER DEFAULT PRIVILEGES IN SCHEMA chat GRANT SELECT, INSERT, UPDATE ON TABLES TO api_service;

-- 5. Grant transform role full access to gold
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA gold TO transform_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA gold GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO transform_role;

-- 6. Inherit readonly_role
GRANT readonly_role TO api_service;
GRANT readonly_role TO airflow_role;

-- 7. Grant api_service access to embeddings
GRANT SELECT ON ALL TABLES IN SCHEMA embeddings TO api_service;
ALTER DEFAULT PRIVILEGES IN SCHEMA embeddings GRANT SELECT ON TABLES TO api_service;

SQL

echo "=== RBAC setup complete ==="
echo "Roles: api_service (read chat/gold + write chat), airflow_role (readonly), transform_role (read/write gold)"
