-- Esquema inicial de PostgreSQL para Sofia AI DataOps.
-- Objetivo: guardar los analisis de incidentes generados por la plataforma.

CREATE TABLE IF NOT EXISTS incident_analyses (
    id UUID PRIMARY KEY,
    dag_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    failure_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    summary TEXT NOT NULL,
    root_cause TEXT,
    recommendations JSONB NOT NULL DEFAULT '[]'::jsonb,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    retrieved_context JSONB NOT NULL DEFAULT '[]'::jsonb,
    source TEXT NOT NULL DEFAULT 'manual',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_incident_analyses_dag_task
    ON incident_analyses (dag_id, task_id);

CREATE INDEX IF NOT EXISTS idx_incident_analyses_created_at
    ON incident_analyses (created_at DESC);
