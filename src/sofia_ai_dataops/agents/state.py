"""Estado compartido del grafo de incidentes.

Objetivo: definir las claves que los nodos leen y escriben durante el analisis.
"""

from typing import Any, TypedDict

from sofia_ai_dataops.schemas.incidents import FailureType, Severity


class IncidentGraphState(TypedDict, total=False):
    dag_id: str
    task_id: str
    run_id: str
    logs: str
    metadata: dict[str, Any]
    retrieved_context: list[str]
    failure_type: FailureType
    severity: Severity
    summary: str
    root_cause: str
    recommendations: list[str]
