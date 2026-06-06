"""Nodo de recomendacion de acciones.

Objetivo: convertir la clasificacion del incidente en pasos concretos de remediacion.
"""

from sofia_ai_dataops.agents.state import IncidentGraphState


def recommend_actions(state: IncidentGraphState) -> IncidentGraphState:
    failure_type = state.get("failure_type", "unknown")
    context = state.get("retrieved_context", [])

    recommendations_by_type = {
        "connectivity": [
            "Check database or service network reachability from the Airflow worker.",
            "Validate credentials, DNS resolution, firewall rules, and connection pool limits.",
            "Retry the task after confirming the downstream dependency is healthy.",
        ],
        "permissions": [
            "Verify the Airflow connection user and secret backend value.",
            "Confirm the task has access to the target dataset, bucket, or service account.",
        ],
        "infrastructure": [
            "Inspect worker disk, memory, and scheduler health.",
            "Scale or recycle unhealthy workers before retrying the DAG run.",
        ],
        "upstream": [
            "Check the upstream service health, status page, and recent deploys.",
            "Retry only after confirming the dependency is available again.",
            "Consider adding backoff, retries, or circuit-breaker behavior for this dependency.",
        ],
        "unknown": [
            "Inspect the complete task log around the first exception.",
            "Compare with recent DAG, dependency, and environment changes.",
        ],
    }

    root_cause = (
        f"Likely {failure_type} failure. Similar context found: {len(context)} records."
        if context
        else f"Likely {failure_type} failure. No similar incidents were retrieved."
    )

    return {
        **state,
        "root_cause": root_cause,
        "recommendations": recommendations_by_type.get(
            failure_type, recommendations_by_type["unknown"]
        ),
    }
