"""Endpoint de metricas operacionales en memoria.

Objetivo: exponer conteos de ultimas 24h (total, por tipo, por severidad, fallbacks)
sin consultar base de datos. Los datos se resetean al reiniciar el proceso.
"""

from fastapi import APIRouter
from pydantic import BaseModel

from sofia_ai_dataops.observability.metrics import get_metrics_collector

router = APIRouter(tags=["metrics"])


class MetricsResponse(BaseModel):
    total_analyses: int
    by_failure_type: dict[str, int]
    by_severity: dict[str, int]
    fallback_triggered: int
    window_hours: int


@router.get("/metrics", response_model=MetricsResponse)
def get_metrics() -> MetricsResponse:
    """Metricas operacionales de las ultimas 24h en memoria.

    Los contadores se resetean si el proceso se reinicia.
    """
    data = get_metrics_collector().snapshot()
    return MetricsResponse(
        total_analyses=data["total_analyses"],
        by_failure_type=data["by_failure_type"],
        by_severity=data["by_severity"],
        fallback_triggered=data["fallback_triggered"],
        window_hours=data["window_hours"],
    )
