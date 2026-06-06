"""Normalizacion de payloads de Airflow.

Objetivo: convertir metadata y logs en texto consistente para agentes, embeddings y auditoria.
"""

from typing import Any

from sofia_ai_dataops.schemas.airflow import AirflowTaskFailureEvent
from sofia_ai_dataops.schemas.incidents import IncidentAnalysisRequest


def normalize_airflow_log(payload: IncidentAnalysisRequest) -> str:
    return "\n".join(
        [
            f"DAG: {payload.dag_id}",
            f"Task: {payload.task_id}",
            f"Run: {payload.run_id}",
            payload.logs.strip(),
        ]
    )


def airflow_failure_to_incident(event: AirflowTaskFailureEvent) -> IncidentAnalysisRequest:
    metadata: dict[str, Any] = {
        "try_number": event.try_number,
        "log_url": event.log_url,
        "execution_date": event.execution_date.isoformat() if event.execution_date else None,
        "hostname": event.hostname,
        "operator": event.operator,
        **event.metadata,
    }
    return IncidentAnalysisRequest(
        dag_id=event.dag_id,
        task_id=event.task_id,
        run_id=event.run_id,
        logs="\n".join(
            [
                f"DAG: {event.dag_id}",
                f"Task: {event.task_id}",
                f"Run: {event.run_id}",
                f"Error: {event.error.strip()}",
            ]
        ),
        metadata={key: value for key, value in metadata.items() if value is not None},
        source="airflow",
    )
