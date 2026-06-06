"""Endpoints operativos de memoria vectorial.

Objetivo: inspeccionar y reconstruir la memoria Qdrant usada para recuperar incidentes similares.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from sofia_ai_dataops.api.dependencies import get_memory_service
from sofia_ai_dataops.services.memory_service import (
    IncidentMemoryService,
    MemoryStatus,
    ReindexResult,
)

router = APIRouter(prefix="/memory", tags=["memory"])


@router.get("/status", response_model=MemoryStatus)
def get_memory_status(
    service: Annotated[IncidentMemoryService, Depends(get_memory_service)],
) -> MemoryStatus:
    return service.status()


@router.post("/reindex", response_model=ReindexResult)
def reindex_memory(
    service: Annotated[IncidentMemoryService, Depends(get_memory_service)],
    limit: Annotated[int, Query(ge=1, le=10_000)] = 1000,
) -> ReindexResult:
    return service.reindex_recent(limit=limit)
