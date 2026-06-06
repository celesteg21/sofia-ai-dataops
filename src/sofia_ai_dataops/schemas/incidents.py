"""Schemas para analisis de incidentes.

Objetivo: validar requests de Airflow y estructurar respuestas de diagnostico.
"""

from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

FailureType = Literal["connectivity", "permissions", "infrastructure", "upstream", "unknown"]
Severity = Literal["low", "medium", "high", "critical"]


class IncidentAnalysisRequest(BaseModel):
    dag_id: str = Field(min_length=1)
    task_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    logs: str = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)
    source: str = "manual"


class IncidentAnalysisResponse(BaseModel):
    analysis_id: UUID
    dag_id: str
    task_id: str
    run_id: str
    failure_type: FailureType
    severity: Severity
    summary: str
    root_cause: str
    recommendations: list[str]
    metadata: dict[str, Any] = Field(default_factory=dict)
    retrieved_context: list[str] = Field(default_factory=list)
    source: str = "manual"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
