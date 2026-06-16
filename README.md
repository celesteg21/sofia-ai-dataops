# Sofia AI DataOps

Sofia is an AI resolution platform for DataOps — focused on diagnosing, resolving, and preventing incidents in data ecosystems.

When a pipeline fails, engineers spend hours gathering context across logs, metadata, runbooks, and data quality results. Sofia does that automatically and returns a structured diagnosis: what broke, why, what to do now, and how to prevent it from happening again.

## Stack

- Python 3.11
- FastAPI
- Pydantic v2
- Docker / Docker Compose
- Mock LLM (no model required) — prepared for Ollama

## Quickstart

```bash
cp .env.example .env
make setup
make run
```

API is available at `http://localhost:8000`.

## Test the endpoint

```bash
curl -X POST http://localhost:8000/incidents/analyze \
  -H "Content-Type: application/json" \
  -d '{"incident_id": "inc_001"}'
```

Response:

```json
{
  "incident_id": "inc_001",
  "summary": "Pipeline 'daily_revenue' failed. Error: PartitionNotFoundError...",
  "probable_root_cause": "Table raw.transactions last updated 2026-06-03. Expected freshness: 2h. Actual lag: 29h.",
  "evidence": [
    "ERROR [daily_revenue] PartitionNotFoundError: Partition dt=2026-06-04 does not exist...",
    "Data quality: Table raw.transactions last updated 2026-06-03..."
  ],
  "business_impact": "Reports at risk: Revenue Dashboard, CFO Daily Brief.",
  "recommended_action": "1. Check status of ingestion_transactions...",
  "long_term_improvement": "Add a freshness check sensor before running dependent report pipelines.",
  "confidence": "medium"
}
```

## Docker

```bash
cp .env.example .env
docker compose up --build
```

To run with a local Ollama model:

```bash
docker compose --profile ollama up --build
# Then set LLM_BACKEND=ollama in .env
```

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/incidents/analyze` | Analyze an incident by ID |

## Project Structure

```
app/
  main.py                   FastAPI app
  api/routes.py             Endpoints
  core/config.py            Settings (env vars)
  core/schemas.py           Pydantic input/output contracts
  services/
    incident_service.py     Main analysis flow
    context_service.py      Gathers context from all tools
    recommendation_service.py  Delegates to LLM
    llm_service.py          Abstract LLM + Mock + Ollama stub
  tools/
    log_reader.py           Reads pipeline logs
    metadata_reader.py      Reads pipeline metadata
    runbook_reader.py       Keyword-based runbook lookup
    orchestrator_adapter.py Base interface for orchestrator integrations
  mock_environment/
    incidents/              Incident definitions (JSON)
    logs/                   Pipeline execution logs
    metadata/               Pipeline metadata and dependencies
    runbooks/               Structured remediation playbooks
    quality_results/        Data quality check outputs
tests/
  test_incident_service.py
  test_context_service.py
docs/
  architecture.md
  roadmap.md
  product_vision.md
```

## Adding a new incident

1. Create `app/mock_environment/incidents/<id>.json`
2. Optionally add matching files under `logs/`, `metadata/`, `runbooks/`, `quality_results/`
3. Call `POST /incidents/analyze` with `{"incident_id": "<id>"}`

## Quality

```bash
make lint
make test
```

## Architecture

See [docs/architecture.md](docs/architecture.md) for the layer diagram and design decisions.

## Roadmap

See [docs/roadmap.md](docs/roadmap.md) for V0.1 through V1.0.

## Product Vision

See [docs/product_vision.md](docs/product_vision.md) for the full vision and design principles.
