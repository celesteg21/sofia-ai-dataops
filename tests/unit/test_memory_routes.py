"""Tests de endpoints operativos de memoria.

Objetivo: validar que Swagger/API puede consultar estado y disparar reindexado de Qdrant.
"""

from fastapi.testclient import TestClient

from sofia_ai_dataops.api.app import create_app
from sofia_ai_dataops.api.dependencies import get_memory_service
from sofia_ai_dataops.services.memory_service import MemoryStatus, ReindexResult


class FakeMemoryService:
    def status(self) -> MemoryStatus:
        return MemoryStatus(postgres_analyses=6, qdrant_points=6, is_in_sync=True)

    def reindex_recent(self, limit: int = 1000) -> ReindexResult:
        return ReindexResult(total_available=6, indexed=min(limit, 6), limit=limit)


def test_memory_status_endpoint() -> None:
    app = create_app()
    app.dependency_overrides[get_memory_service] = lambda: FakeMemoryService()
    client = TestClient(app)

    response = client.get("/api/v1/memory/status")

    assert response.status_code == 200
    assert response.json() == {
        "postgres_analyses": 6,
        "qdrant_points": 6,
        "is_in_sync": True,
    }


def test_memory_reindex_endpoint() -> None:
    app = create_app()
    app.dependency_overrides[get_memory_service] = lambda: FakeMemoryService()
    client = TestClient(app)

    response = client.post("/api/v1/memory/reindex?limit=2")

    assert response.status_code == 200
    assert response.json() == {
        "total_available": 6,
        "indexed": 2,
        "limit": 2,
    }
