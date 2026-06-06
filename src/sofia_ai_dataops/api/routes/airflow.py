"""Endpoints de ingesta para Airflow.

Objetivo: recibir eventos operativos de Airflow y transformarlos en incidentes analizables.
"""

from typing import Annotated

from fastapi import APIRouter, Depends

from sofia_ai_dataops.api.dependencies import get_incident_service
from sofia_ai_dataops.ingestion.airflow import airflow_failure_to_incident
from sofia_ai_dataops.schemas.airflow import AirflowTaskFailureEvent
from sofia_ai_dataops.schemas.incidents import IncidentAnalysisResponse
from sofia_ai_dataops.services.incident_service import IncidentAnalysisService

router = APIRouter(prefix="/airflow", tags=["airflow"])


@router.post("/task-failures", response_model=IncidentAnalysisResponse)
async def ingest_task_failure(
    event: AirflowTaskFailureEvent,
    service: Annotated[IncidentAnalysisService, Depends(get_incident_service)],
) -> IncidentAnalysisResponse:
    incident = airflow_failure_to_incident(event)
    return await service.analyze(incident)
