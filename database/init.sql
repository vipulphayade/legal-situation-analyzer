CREATE EXTENSION IF NOT EXISTS vector;

-- All tables (schema_version, bylaws, bylaw_relations, query_logs,
-- session_store) are managed by Alembic and created during api
-- startup via run_migrations().
