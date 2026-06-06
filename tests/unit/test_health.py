"""Tests del endpoint de salud.

Objetivo: validar que la API responde correctamente para checks basicos de disponibilidad.
"""

from fastapi.testclient import TestClient

from sofia_ai_dataops.api.app import create_app


def test_health_endpoint_returns_ok() -> None:
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
