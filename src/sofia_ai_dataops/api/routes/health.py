"""Endpoint de salud.

Objetivo: permitir checks simples de disponibilidad para Docker, CI y monitoreo.
"""

from fastapi import APIRouter

from sofia_ai_dataops.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok")
