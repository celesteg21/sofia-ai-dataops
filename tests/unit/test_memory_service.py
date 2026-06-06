"""Tests de reconstruccion de memoria vectorial.

Objetivo: validar que Sofia puede reindexar en Qdrant los analisis guardados en PostgreSQL.
"""

from typing import cast
from uuid import uuid4

from sofia_ai_dataops.db.postgres import IncidentAnalysisRepository
from sofia_ai_dataops.db.qdrant import IncidentVectorStore
from sofia_ai_dataops.schemas.incidents import IncidentAnalysisResponse
from sofia_ai_dataops.services.memory_service import IncidentMemoryService


class FakeRepository:
    def __init__(self, analyses: list[IncidentAnalysisResponse]) -> None:
        self._analyses = analyses

    def list_recent(self, limit: int = 20) -> list[IncidentAnalysisResponse]:
        return self._analyses[:limit]

    def count(self) -> int:
        return len(self._analyses)


class FakeVectorStore:
    def __init__(self, indexed_count: int = 0) -> None:
        self.indexed: list[IncidentAnalysisResponse] = []
        self._indexed_count = indexed_count

    def index_analysis(self, analysis: IncidentAnalysisResponse) -> None:
        self.indexed.append(analysis)

    def count_indexed(self) -> int:
        return self._indexed_count


def test_memory_service_reindexes_recent_analyses() -> None:
    analyses = [
        IncidentAnalysisResponse(
            analysis_id=uuid4(),
            dag_id="daily_sales",
            task_id="load_warehouse",
            run_id="run-1",
            failure_type="connectivity",
            severity="high",
            summary="Database timeout.",
            root_cause="Database was unavailable.",
            recommendations=["Check database"],
        ),
        IncidentAnalysisResponse(
            analysis_id=uuid4(),
            dag_id="daily_sales",
            task_id="read_secret",
            run_id="run-2",
            failure_type="permissions",
            severity="medium",
            summary="Permission denied.",
            root_cause="Secret backend rejected access.",
            recommendations=["Check secrets"],
        ),
    ]
    repository = FakeRepository(analyses)
    vector_store = FakeVectorStore()
    service = IncidentMemoryService(
        repository=cast(IncidentAnalysisRepository, repository),
        vector_store=cast(IncidentVectorStore, vector_store),
    )

    result = service.reindex_recent(limit=1)

    assert result.total_available == 2
    assert result.indexed == 1
    assert vector_store.indexed == [analyses[0]]


def test_memory_service_reports_sync_status() -> None:
    analyses = [
        IncidentAnalysisResponse(
            analysis_id=uuid4(),
            dag_id="daily_sales",
            task_id="load_warehouse",
            run_id="run-1",
            failure_type="connectivity",
            severity="high",
            summary="Database timeout.",
            root_cause="Database was unavailable.",
            recommendations=["Check database"],
        )
    ]
    service = IncidentMemoryService(
        repository=cast(IncidentAnalysisRepository, FakeRepository(analyses)),
        vector_store=cast(IncidentVectorStore, FakeVectorStore(indexed_count=1)),
    )

    status = service.status()

    assert status.postgres_analyses == 1
    assert status.qdrant_points == 1
    assert status.is_in_sync is True
