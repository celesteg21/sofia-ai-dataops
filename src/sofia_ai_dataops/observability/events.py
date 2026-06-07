"""Eventos de aplicacion.

Objetivo: registrar hechos relevantes del dominio con structlog:
incidentes analizados y ciclo de vida de cada nodo del grafo LangGraph.
"""

import structlog

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Eventos de dominio
# ---------------------------------------------------------------------------


def log_incident_analyzed(dag_id: str, task_id: str, severity: str) -> None:
    logger.info("incident_analyzed", dag_id=dag_id, task_id=task_id, severity=severity)


# ---------------------------------------------------------------------------
# Ciclo de vida de nodos
# ---------------------------------------------------------------------------


def log_node_started(node_name: str, dag_id: str, task_id: str) -> None:
    logger.debug("node_started", node=node_name, dag_id=dag_id, task_id=task_id)


def log_node_completed(
    node_name: str,
    dag_id: str,
    task_id: str,
    duration_ms: float,
    model_used: str | None = None,
    fallback_triggered: bool = False,
) -> None:
    logger.info(
        "node_completed",
        node=node_name,
        dag_id=dag_id,
        task_id=task_id,
        duration_ms=round(duration_ms, 2),
        model_used=model_used,
        fallback_triggered=fallback_triggered,
    )


def log_node_failed(
    node_name: str,
    dag_id: str,
    task_id: str,
    duration_ms: float,
) -> None:
    logger.error(
        "node_failed",
        node=node_name,
        dag_id=dag_id,
        task_id=task_id,
        duration_ms=round(duration_ms, 2),
        exc_info=True,
    )
