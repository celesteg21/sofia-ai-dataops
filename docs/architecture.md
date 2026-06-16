# Sofia AI DataOps — Architecture

## Layer Overview

```
HTTP Request
     │
     ▼
┌─────────────┐
│  API layer  │  app/api/routes.py — FastAPI endpoints, input validation
└──────┬──────┘
       │
       ▼
┌──────────────────┐
│  IncidentService │  app/services/incident_service.py — orchestrates the analysis flow
└──────┬───────────┘
       │
       ├──────────────────────────────┐
       ▼                              ▼
┌─────────────────┐        ┌──────────────────────┐
│ ContextService  │        │ RecommendationService │
│                 │        │                       │
│ LogReader       │        │ LLMService            │
│ MetadataReader  │        │  MockLLMService       │
│ RunbookReader   │        │  OllamaLLMService     │
│ quality results │        └──────────────────────┘
└─────────────────┘
       │
       ▼
app/mock_environment/
  incidents/        incident definition JSON
  logs/             pipeline execution logs
  metadata/         pipeline metadata and dependencies
  runbooks/         structured remediation playbooks
  quality_results/  data quality check outputs
```

## Responsibilities by Module

| Module | Responsibility |
|--------|---------------|
| `app/main.py` | FastAPI app setup and router wiring |
| `app/api/routes.py` | HTTP endpoints, request/response types |
| `app/core/config.py` | Settings from environment variables |
| `app/core/schemas.py` | Pydantic contracts for API input/output |
| `app/services/incident_service.py` | Entry point: load incident, gather context, generate analysis |
| `app/services/context_service.py` | Orchestrates all context-reading tools |
| `app/services/recommendation_service.py` | Delegates to LLMService |
| `app/services/llm_service.py` | Abstract LLM interface + Mock and Ollama implementations |
| `app/tools/log_reader.py` | Reads pipeline log files |
| `app/tools/metadata_reader.py` | Reads pipeline metadata JSON |
| `app/tools/runbook_reader.py` | Keyword-based runbook lookup |
| `app/tools/orchestrator_adapter.py` | Base interface + Mock for orchestrator integrations |

## Key Design Decisions

**Framework-agnostic.** There is no LangGraph, CrewAI, or Strands dependency. The `IncidentService` is a plain Python class that can be wired into any agent framework later without changing the business logic.

**LLM as a plug.** `LLMService` is an abstract class. `MockLLMService` derives the response from structured context without a model. `OllamaLLMService` is a stub ready for a real implementation. Switching is a one-line config change (`LLM_BACKEND=ollama`).

**OrchestratorAdapter as a seam.** Real orchestrators (Airflow, Dagster, Prefect) will implement the `OrchestratorAdapter` interface. The rest of the system never talks to orchestrators directly.

**File-based mock environment.** All context data lives in `app/mock_environment/`. This makes the system easy to run locally, easy to extend with new test cases, and ready to swap for real data sources (databases, APIs) without changing the service layer.

## Adding a New Incident

1. Add `app/mock_environment/incidents/<incident_id>.json`
2. Optionally add matching files under `logs/`, `metadata/`, `runbooks/`, `quality_results/`
3. Call `POST /incidents/analyze` with `{"incident_id": "<incident_id>"}`

## Adding a New Orchestrator

1. Create a class in `app/tools/` that extends `OrchestratorAdapter`
2. Implement `get_run_status`, `trigger_run`, and `get_logs`
3. Wire it into `ContextService` or a new service for live context gathering
