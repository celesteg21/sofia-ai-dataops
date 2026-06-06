"""Endpoints para incidentes de Airflow.

Objetivo: recibir incidentes y devolver un diagnostico producido por el servicio de analisis.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from sofia_ai_dataops.api.dependencies import get_incident_service
from sofia_ai_dataops.schemas.incidents import IncidentAnalysisRequest, IncidentAnalysisResponse
from sofia_ai_dataops.services.incident_service import IncidentAnalysisService

router = APIRouter(prefix="/incidents", tags=["incidents"])


@router.get("", response_model=list[IncidentAnalysisResponse])
def list_recent_incident_analyses(
    service: Annotated[IncidentAnalysisService, Depends(get_incident_service)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[IncidentAnalysisResponse]:
    return service.list_recent_analyses(limit=limit)


@router.get("/{analysis_id}", response_model=IncidentAnalysisResponse)
def get_incident_analysis(
    analysis_id: UUID,
    service: Annotated[IncidentAnalysisService, Depends(get_incident_service)],
) -> IncidentAnalysisResponse:
    analysis = service.get_analysis(analysis_id)
    if analysis is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incident analysis not found",
        )
    return analysis


@router.post("/analyze", response_model=IncidentAnalysisResponse)
async def analyze_incident(
    payload: IncidentAnalysisRequest,
    service: Annotated[IncidentAnalysisService, Depends(get_incident_service)],
) -> IncidentAnalysisResponse:
    return await service.analyze(payload)
