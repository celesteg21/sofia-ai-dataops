"""Nodo de clasificacion de incidentes.

Objetivo: inferir tipo de falla y severidad inicial a partir de patrones simples en los logs.
"""

from sofia_ai_dataops.agents.state import IncidentGraphState
from sofia_ai_dataops.schemas.incidents import FailureType, Severity


def classify_incident(state: IncidentGraphState) -> IncidentGraphState:
    logs = state.get("logs", "").lower()
    failure_type: FailureType
    severity: Severity

    if "timeout" in logs or "could not connect" in logs:
        failure_type = "connectivity"
        severity = "high"
    elif "permission" in logs or "access denied" in logs:
        failure_type = "permissions"
        severity = "medium"
    elif "no space left" in logs or "disk" in logs:
        failure_type = "infrastructure"
        severity = "critical"
    elif "upstream" in logs or "503" in logs or "service unavailable" in logs:
        failure_type = "upstream"
        severity = "high"
    else:
        failure_type = "unknown"
        severity = "medium"

    return {
        **state,
        "failure_type": failure_type,
        "severity": severity,
        "summary": f"Airflow task failed with likely {failure_type} issue.",
    }
