# Objetivo del documento:
# describir las fronteras tecnicas de Sofia AI DataOps y como evolucionar la arquitectura.

# Sofia AI DataOps Architecture

Sofia AI DataOps separates operational concerns into a small set of boundaries:

- **API layer**: accepts Airflow incident payloads and returns analysis results.
- **Service layer**: orchestrates use cases and keeps HTTP concerns out of agent code.
- **Agent layer**: owns LangGraph state, nodes, prompts, and routing decisions.
- **Persistence layer**: stores durable analysis records in PostgreSQL.
- **Retrieval layer**: indexes incident/log context in Qdrant for similar-incident recall.
- **Observability layer**: centralizes structured logs, tracing hooks, and future metrics.

The first graph is intentionally modest:

1. Normalize the incident payload.
2. Classify likely failure type and severity.
3. Retrieve similar historical context filtered by failure type when available.
4. Produce a concise root-cause hypothesis and remediation plan.

Production hardening should add prompt/version registries, offline eval datasets, human review flows,
PII redaction, model fallback policy, and per-tenant data isolation before broad rollout.
