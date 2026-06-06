"""Tests del dashboard operativo.

Objetivo: validar que la primera consola visual se sirve desde FastAPI.
"""

from fastapi.testclient import TestClient

from sofia_ai_dataops.api.app import create_app


def test_dashboard_returns_html() -> None:
    client = TestClient(create_app())

    response = client.get("/dashboard")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Sofia AI DataOps" in response.text
    assert "/api/v1/incidents?limit=100" in response.text
    assert "Contexto recuperado" in response.text
    assert "context-status" in response.text
