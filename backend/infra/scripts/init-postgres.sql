-- IDP PostgreSQL Init (Phase 6 Optimized)
-- Runs automatically on first volume creation

-- 1. Airflow metadata database
CREATE DATABASE airflow_db;

\c idp_warehouse;

-- 2. Extensions
CREATE EXTENSION IF NOT EXISTS vector;

-- 3. Schemas
CREATE SCHEMA IF NOT EXISTS gold;
CREATE SCHEMA IF NOT EXISTS embeddings;
CREATE SCHEMA IF NOT EXISTS chat;

-- 4. Phase 6 RBAC Roles
-- Note: These use the admin's power during init.
-- Passwords will be updated via setup_rbac.sh or manually if needed,
-- but for initial spin-up, we create them.

DO $$
BEGIN
    -- Read-only role
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'readonly_role') THEN
        CREATE ROLE readonly_role NOLOGIN;
    END IF;

    -- API Service
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'api_service') THEN
        CREATE ROLE api_service LOGIN PASSWORD 'CHANGE_ME_IN_PROD';
    END IF;

    -- Airflow Role
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'airflow_role') THEN
        CREATE ROLE airflow_role LOGIN PASSWORD 'CHANGE_ME_IN_PROD';
    END IF;

    -- Transform Role
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'transform_role') THEN
        CREATE ROLE transform_role LOGIN PASSWORD 'CHANGE_ME_IN_PROD';
    END IF;
END
$$;

-- 5. Permissions
GRANT USAGE ON SCHEMA gold TO readonly_role, api_service, transform_role, airflow_role;
GRANT USAGE ON SCHEMA chat TO api_service, airflow_role;
GRANT USAGE ON SCHEMA embeddings TO api_service, airflow_role;

-- Gold access
GRANT SELECT ON ALL TABLES IN SCHEMA gold TO readonly_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA gold GRANT SELECT ON TABLES TO readonly_role;
GRANT SELECT ON ALL TABLES IN SCHEMA gold TO api_service;
ALTER DEFAULT PRIVILEGES IN SCHEMA gold GRANT SELECT ON TABLES TO api_service;
GRANT ALL PRIVILEGES ON SCHEMA gold TO transform_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA gold GRANT ALL ON TABLES TO transform_role;

-- Chat access
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA chat TO api_service;
ALTER DEFAULT PRIVILEGES IN SCHEMA chat GRANT SELECT, INSERT, UPDATE ON TABLES TO api_service;

-- Embeddings access
GRANT SELECT ON ALL TABLES IN SCHEMA embeddings TO api_service;
ALTER DEFAULT PRIVILEGES IN SCHEMA embeddings GRANT SELECT ON TABLES TO api_service;

-- 6. Tables (Phase 5)
CREATE TABLE IF NOT EXISTS chat.sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS chat.messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES chat.sessions(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    citations JSONB,
    tokens_used INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_messages_session ON chat.messages(session_id);
