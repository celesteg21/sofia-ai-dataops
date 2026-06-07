"""Caso de uso principal para analizar incidentes.

Objetivo: ejecutar el grafo de IA, persistir el diagnostico y devolver una respuesta HTTP-safe.
"""

from typing import Any, Protocol
from uuid import UUID, uuid4

from sofia_ai_dataops.db.postgres import IncidentAnalysisRepository
from sofia_ai_dataops.db.qdrant import IncidentVectorStore
from sofia_ai_dataops.observability.events import log_incident_analyzed
from sofia_ai_dataops.observability.metrics import get_metrics_collector
from sofia_ai_dataops.schemas.incidents import IncidentAnalysisRequest, IncidentAnalysisResponse


class IncidentGraph(Protocol):
    async def ainvoke(self, input: dict[str, Any]) -> dict[str, Any]:
        ...


class IncidentAnalysisService:
    def __init__(
        self,
        graph: IncidentGraph,
        repository: IncidentAnalysisRepository,
        vector_store: IncidentVectorStore,
    ) -> None:
        self._graph = graph
        self._repository = repository
        self._vector_store = vector_store

    def get_analysis(self, analysis_id: UUID) -> IncidentAnalysisResponse | None:
        return self._repository.get(analysis_id)

    def list_recent_analyses(self, limit: int = 20) -> list[IncidentAnalysisResponse]:
        return self._repository.list_recent(limit=limit)

    async def analyze(self, payload: IncidentAnalysisRequest) -> IncidentAnalysisResponse:
        state: dict[str, Any] = {
            "dag_id": payload.dag_id,
            "task_id": payload.task_id,
            "run_id": payload.run_id,
            "logs": payload.logs,
            "metadata": payload.metadata,
            "source": payload.source,
        }
        result = await self._graph.ainvoke(state)

        response = IncidentAnalysisResponse(
            analysis_id=uuid4(),
            dag_id=payload.dag_id,
            task_id=payload.task_id,
            run_id=payload.run_id,
            failure_type=result["failure_type"],
            severity=result["severity"],
            summary=result["summary"],
            root_cause=result["root_cause"],
            recommendations=result["recommendations"],
            metadata=payload.metadata,
            retrieved_context=result.get("retrieved_context", []),
            source=payload.source,
        )
        self._repository.save(response)
        self._vector_store.index_analysis(response)
        log_incident_analyzed(payload.dag_id, payload.task_id, response.severity)

        fallback_triggered = bool(result.get("fallback_triggered", False))
        get_metrics_collector().record(
            failure_type=response.failure_type,
            severity=response.severity,
            fallback_triggered=fallback_triggered,
        )

        return response
