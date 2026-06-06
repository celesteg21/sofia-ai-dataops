"""Schemas de eventos provenientes de Airflow.

Objetivo: definir un contrato explicito para fallas de task antes de normalizarlas como incidentes.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AirflowTaskFailureEvent(BaseModel):
    dag_id: str = Field(min_length=1)
    task_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    error: str = Field(min_length=1)
    try_number: int | None = Field(default=None, ge=1)
    log_url: str | None = None
    execution_date: datetime | None = None
    hostname: str | None = None
    operator: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
