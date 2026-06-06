"""Tests de ingesta de eventos Airflow.

Objetivo: validar el contrato Airflow -> Sofia antes de analizar incidentes.
"""

from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient

from sofia_ai_dataops.api.app import create_app
from sofia_ai_dataops.api.dependencies import get_incident_service
from sofia_ai_dataops.ingestion.airflow import airflow_failure_to_incident
from sofia_ai_dataops.schemas.airflow import AirflowTaskFailureEvent
from sofia_ai_dataops.schemas.incidents import IncidentAnalysisRequest, IncidentAnalysisResponse


class FakeIncidentService:
    def __init__(self) -> None:
        self.received_payload: IncidentAnalysisRequest | None = None

    async def analyze(self, payload: IncidentAnalysisRequest) -> IncidentAnalysisResponse:
        self.received_payload = payload
        return IncidentAnalysisResponse(
            analysis_id=uuid4(),
            dag_id=payload.dag_id,
            task_id=payload.task_id,
            run_id=payload.run_id,
            failure_type="upstream",
            severity="high",
            summary="Airflow task failed with likely upstream issue.",
            root_cause="Likely upstream failure. No similar incidents were retrieved.",
            recommendations=["Check the upstream service health."],
            metadata=payload.metadata,
            retrieved_context=[],
            source=payload.source,
        )


def test_airflow_failure_event_normalizes_to_incident_request() -> None:
    event = AirflowTaskFailureEvent(
        dag_id="sofia_lab_upstream_failed",
        task_id="extract_source",
        run_id="manual__2026-06-06T00:00:00+00:00",
        error="Upstream source API returned HTTP 503 Service Unavailable",
        try_number=2,
        log_url="http://localhost:8080/log",
        execution_date=datetime(2026, 6, 6, tzinfo=UTC),
        operator="DecoratedOperator",
        metadata={"environment": "airflow-lab"},
    )

    incident = airflow_failure_to_incident(event)

    assert incident.source == "airflow"
    assert incident.dag_id == event.dag_id
    assert "HTTP 503" in incident.logs
    assert incident.metadata["try_number"] == 2
    assert incident.metadata["environment"] == "airflow-lab"


def test_airflow_task_failure_endpoint_analyzes_normalized_event() -> None:
    app = create_app()
    service = FakeIncidentService()
    app.dependency_overrides[get_incident_service] = lambda: service
    client = TestClient(app)

    response = client.post(
        "/api/v1/airflow/task-failures",
        json={
            "dag_id": "sofia_lab_upstream_failed",
            "task_id": "extract_source",
            "run_id": "manual__2026-06-06T00:00:00+00:00",
            "error": "Upstream source API returned HTTP 503 Service Unavailable",
            "try_number": 1,
            "metadata": {"environment": "airflow-lab"},
        },
    )

    assert response.status_code == 200
    assert response.json()["source"] == "airflow"
    assert service.received_payload is not None
    assert service.received_payload.source == "airflow"
    assert service.received_payload.metadata["environment"] == "airflow-lab"
