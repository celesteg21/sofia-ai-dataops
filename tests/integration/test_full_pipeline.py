"""Tests de integración del pipeline completo.

Objetivo: verificar que el flujo entero —desde evento Airflow hasta análisis persistido
en memoria— funciona correctamente sin servicios externos.

Usa los fixtures de conftest.py para infraestructura en-memoria.
"""

import pytest

from sofia_ai_dataops.ingestion.airflow import airflow_failure_to_incident
from sofia_ai_dataops.schemas.airflow import AirflowTaskFailureEvent
from sofia_ai_dataops.services.incident_service import IncidentAnalysisService


@pytest.mark.asyncio
async def test_db_timeout_dag_full_pipeline(
    db_timeout_event: AirflowTaskFailureEvent,
    incident_service: IncidentAnalysisService,
) -> None:
    """Flujo completo: timeout de DB → clasificado como connectivity/high → persistido."""
    incident = airflow_failure_to_incident(db_timeout_event)

    assert incident.source == "airflow"
    assert incident.dag_id == "sofia_lab_database_timeout"
    assert "timeout" in incident.logs.lower()

    analysis = await incident_service.analyze(incident)

    assert analysis.failure_type == "connectivity"
    assert analysis.severity == "high"
    assert analysis.dag_id == "sofia_lab_database_timeout"
    assert analysis.task_id == "query_warehouse"
    assert analysis.source == "airflow"
    assert len(analysis.recommendations) >= 2
    assert analysis.root_cause

    # verificar persistencia
    persisted = incident_service.get_analysis(analysis.analysis_id)
    assert persisted is not None
    assert persisted.failure_type == "connectivity"
    assert persisted.metadata["warehouse"] == "warehouse-postgres"


@pytest.mark.asyncio
async def test_missing_credentials_dag_full_pipeline(
    missing_credentials_event: AirflowTaskFailureEvent,
    incident_service: IncidentAnalysisService,
) -> None:
    """Flujo completo: access denied → clasificado como permissions/medium → persistido."""
    incident = airflow_failure_to_incident(missing_credentials_event)
    analysis = await incident_service.analyze(incident)

    assert analysis.failure_type == "permissions"
    assert analysis.severity == "medium"
    assert "secret" in " ".join(analysis.recommendations).lower()

    persisted = incident_service.get_analysis(analysis.analysis_id)
    assert persisted is not None
    assert persisted.failure_type == "permissions"


@pytest.mark.asyncio
async def test_upstream_503_dag_full_pipeline(
    upstream_failed_event: AirflowTaskFailureEvent,
    incident_service: IncidentAnalysisService,
) -> None:
    """Flujo completo: HTTP 503 → clasificado como upstream/high → persistido."""
    incident = airflow_failure_to_incident(upstream_failed_event)
    analysis = await incident_service.analyze(incident)

    assert analysis.failure_type == "upstream"
    assert analysis.severity == "high"

    persisted = incident_service.get_analysis(analysis.analysis_id)
    assert persisted is not None


@pytest.mark.asyncio
async def test_causal_chain_both_events_pipeline(
    causal_empty_ingestion_event: AirflowTaskFailureEvent,
    causal_missing_partition_event: AirflowTaskFailureEvent,
    incident_service: IncidentAnalysisService,
) -> None:
    """Falla causal: ingesta vacía → transformación con partición faltante.

    Ambas se clasifican como upstream, ya que la cadena causal es una
    dependencia de datos faltante aguas arriba.
    """
    ingest_incident = airflow_failure_to_incident(causal_empty_ingestion_event)
    transform_incident = airflow_failure_to_incident(causal_missing_partition_event)

    ingest_analysis = await incident_service.analyze(ingest_incident)
    transform_analysis = await incident_service.analyze(transform_incident)

    assert ingest_analysis.failure_type == "upstream"
    assert transform_analysis.failure_type == "upstream"

    # ambos persistidos y recuperables
    all_analyses = incident_service.list_recent_analyses(limit=10)
    analysis_ids = {a.analysis_id for a in all_analyses}
    assert ingest_analysis.analysis_id in analysis_ids
    assert transform_analysis.analysis_id in analysis_ids


@pytest.mark.asyncio
async def test_second_identical_incident_retrieves_memory_context(
    db_timeout_event: AirflowTaskFailureEvent,
    seeded_incident_service: IncidentAnalysisService,
) -> None:
    """Un incidente idéntico a uno histórico recupera contexto similar de Qdrant.

    seeded_incident_service tiene un incidente de conectividad pre-cargado en memoria.
    El nuevo análisis debe encontrarlo en retrieved_context.
    """
    incident = airflow_failure_to_incident(db_timeout_event)
    analysis = await seeded_incident_service.analyze(incident)

    assert analysis.failure_type == "connectivity"
    assert len(analysis.retrieved_context) > 0
    assert any(
        "connectivity" in ctx or "timeout" in ctx.lower()
        for ctx in analysis.retrieved_context
    )


@pytest.mark.asyncio
async def test_list_recent_analyses_after_multiple_failures(
    db_timeout_event: AirflowTaskFailureEvent,
    upstream_failed_event: AirflowTaskFailureEvent,
    missing_credentials_event: AirflowTaskFailureEvent,
    incident_service: IncidentAnalysisService,
) -> None:
    """Después de analizar tres DAGs distintos, list_recent devuelve los tres."""
    for event in [db_timeout_event, upstream_failed_event, missing_credentials_event]:
        incident = airflow_failure_to_incident(event)
        await incident_service.analyze(incident)

    analyses = incident_service.list_recent_analyses(limit=10)
    assert len(analyses) == 3
    failure_types = {a.failure_type for a in analyses}
    assert "connectivity" in failure_types
    assert "upstream" in failure_types
    assert "permissions" in failure_types
