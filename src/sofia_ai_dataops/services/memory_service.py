"""Casos de uso para memoria vectorial.

Objetivo: reconstruir o mantener la memoria semantica de incidentes a partir de datos durables.
"""

from pydantic import BaseModel

from sofia_ai_dataops.db.postgres import IncidentAnalysisRepository
from sofia_ai_dataops.db.qdrant import IncidentVectorStore


class ReindexResult(BaseModel):
    total_available: int
    indexed: int
    limit: int


class MemoryStatus(BaseModel):
    postgres_analyses: int
    qdrant_points: int
    is_in_sync: bool


class IncidentMemoryService:
    def __init__(
        self,
        repository: IncidentAnalysisRepository,
        vector_store: IncidentVectorStore,
    ) -> None:
        self._repository = repository
        self._vector_store = vector_store

    def reindex_recent(self, limit: int = 1000) -> ReindexResult:
        analyses = self._repository.list_recent(limit=limit)
        for analysis in analyses:
            self._vector_store.index_analysis(analysis)

        return ReindexResult(
            total_available=self._repository.count(),
            indexed=len(analyses),
            limit=limit,
        )

    def status(self) -> MemoryStatus:
        postgres_analyses = self._repository.count()
        qdrant_points = self._vector_store.count_indexed()
        return MemoryStatus(
            postgres_analyses=postgres_analyses,
            qdrant_points=qdrant_points,
            is_in_sync=qdrant_points >= postgres_analyses,
        )
