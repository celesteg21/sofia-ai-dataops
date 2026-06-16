# Sofia AI DataOps — Roadmap

## V0.1 — Incident Analyzer (current)

**Goal:** Given an incident ID, Sofia reads local context and returns a structured diagnosis.

- `POST /incidents/analyze` endpoint
- Reads incident JSON, pipeline logs, metadata, runbooks, and quality results from local files
- Returns: summary, probable root cause, evidence, business impact, recommended action, long-term improvement
- Mock LLM (deterministic, no model required)
- Framework-agnostic architecture
- Extensible OrchestratorAdapter interface

## V0.2 — Runbook RAG

**Goal:** Sofia can semantically search across a library of runbooks instead of using keyword matching.

- Embed runbooks at startup (local embedding model via Ollama)
- Retrieve top-k relevant runbooks by cosine similarity
- Rank by recency and incident type
- No cloud dependency required

## V0.3 — Metadata & Lineage Awareness

**Goal:** Sofia understands upstream/downstream relationships and can trace impact automatically.

- Parse lineage graphs from metadata files or a local lineage store
- Identify all downstream reports and datasets affected by an incident
- Include lineage evidence in the analysis response

## V0.4 — Orchestrator Adapters

**Goal:** Sofia can pull live context from real orchestrators.

- `AirflowAdapter`: read DAG/task status, logs, run history via Airflow REST API
- `DagsterAdapter`: read asset materializations and run logs
- `PrefectAdapter`: read flow run state and logs
- `StepFunctionsAdapter`: read execution history from AWS Step Functions
- All adapters implement the `OrchestratorAdapter` interface from V0.1

## V0.5 — Recommendation Engine for Recurring Incidents

**Goal:** Sofia detects patterns across past incidents and generates structural improvements.

- Track incident history locally (SQLite or JSON store)
- Detect recurring failure patterns (same pipeline, same error type)
- Produce prioritized improvement recommendations for the engineering team

## V0.6 — Human Approval Actions

**Goal:** Sofia proposes actions that a human can approve or reject before execution.

- Sofia generates a remediation plan with specific actions
- Human reviews and approves via CLI or API
- Sofia executes approved actions via the relevant OrchestratorAdapter
- Full audit trail of proposed vs. executed actions

## V1.0 — Multi-orchestrator DataOps Copilot

**Goal:** Sofia is the single pane of glass for DataOps incident resolution across the full data stack.

- Unified incident view across all connected orchestrators
- Agent framework integration (LangGraph, CrewAI, Strands — pluggable)
- Real LLM integration for natural language diagnosis
- Slack / PagerDuty integration for alert routing
- Dashboard for incident history and pattern analysis
