"""Schemas del endpoint de salud.

Objetivo: declarar una respuesta simple y estable para checks de disponibilidad.
"""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
