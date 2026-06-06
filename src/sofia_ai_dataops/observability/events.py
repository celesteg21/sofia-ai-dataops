"""Eventos de aplicacion.

Objetivo: registrar hechos relevantes del dominio, como un incidente analizado.
"""

import structlog

logger = structlog.get_logger()


def log_incident_analyzed(dag_id: str, task_id: str, severity: str) -> None:
    logger.info("incident_analyzed", dag_id=dag_id, task_id=task_id, severity=severity)
