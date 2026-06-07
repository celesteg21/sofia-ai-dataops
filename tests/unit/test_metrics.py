"""Tests para MetricsCollector y el endpoint GET /api/v1/metrics.

Cubre: record/snapshot, ventana 24h, conteo de fallbacks, thread-safety
y la respuesta HTTP del endpoint.
"""

import threading
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from sofia_ai_dataops.api.app import create_app
from sofia_ai_dataops.observability.metrics import MetricsCollector

# ---------------------------------------------------------------------------
# MetricsCollector — unit
# ---------------------------------------------------------------------------


class TestMetricsCollector:
    def setup_method(self) -> None:
        self.collector = MetricsCollector()

    def test_empty_snapshot(self) -> None:
        snap = self.collector.snapshot()
        assert snap["total_analyses"] == 0
        assert snap["by_failure_type"] == {}
        assert snap["by_severity"] == {}
        assert snap["fallback_triggered"] == 0
        assert snap["window_hours"] == 24

    def test_record_increments_counts(self) -> None:
        self.collector.record("connectivity", "high", fallback_triggered=False)
        self.collector.record("permissions", "medium", fallback_triggered=True)
        snap = self.collector.snapshot()
        assert snap["total_analyses"] == 2
        assert snap["by_failure_type"]["connectivity"] == 1
        assert snap["by_failure_type"]["permissions"] == 1
        assert snap["by_severity"]["high"] == 1
        assert snap["by_severity"]["medium"] == 1
        assert snap["fallback_triggered"] == 1

    def test_fallback_count_only_counts_true(self) -> None:
        self.collector.record("connectivity", "high", fallback_triggered=True)
        self.collector.record("upstream", "high", fallback_triggered=False)
        self.collector.record("unknown", "medium", fallback_triggered=True)
        snap = self.collector.snapshot()
        assert snap["fallback_triggered"] == 2

    def test_same_type_accumulates(self) -> None:
        for _ in range(5):
            self.collector.record("connectivity", "high", fallback_triggered=False)
        snap = self.collector.snapshot()
        assert snap["by_failure_type"]["connectivity"] == 5

    def test_entries_outside_24h_window_are_excluded(self) -> None:
        """Entradas mas viejas que 24h no deben aparecer en el snapshot."""
        self.collector.record("connectivity", "high", fallback_triggered=False)

        # Falsifica el created_at de la unica entrada para que quede fuera de ventana.
        old_time = datetime.now(UTC) - timedelta(hours=25)
        with self.collector._lock:
            self.collector._entries[0].created_at = old_time

        snap = self.collector.snapshot()
        assert snap["total_analyses"] == 0
        assert snap["by_failure_type"] == {}

    def test_snapshot_prunes_old_entries(self) -> None:
        """Despues del snapshot, las entradas viejas deben eliminarse de _entries."""
        self.collector.record("connectivity", "high", fallback_triggered=False)
        old_time = datetime.now(UTC) - timedelta(hours=25)
        with self.collector._lock:
            self.collector._entries[0].created_at = old_time

        self.collector.snapshot()
        with self.collector._lock:
            assert len(self.collector._entries) == 0

    def test_thread_safety_concurrent_records(self) -> None:
        """Multiples threads escribiendo concurrentemente no deben perder registros."""
        errors: list[Exception] = []

        def write_records() -> None:
            try:
                for _ in range(50):
                    self.collector.record("connectivity", "high", fallback_triggered=False)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=write_records) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == [], f"Errores concurrentes: {errors}"
        snap = self.collector.snapshot()
        assert snap["total_analyses"] == 500  # 10 threads * 50 records


# ---------------------------------------------------------------------------
# Endpoint GET /api/v1/metrics
# ---------------------------------------------------------------------------


@pytest.fixture
def api_client() -> TestClient:
    app = create_app()
    return TestClient(app)


def test_metrics_endpoint_returns_empty_on_fresh_start(api_client: TestClient) -> None:
    """Un proceso recien iniciado debe devolver todos los contadores en cero."""
    fresh_collector = MetricsCollector()
    with patch(
        "sofia_ai_dataops.api.routes.metrics.get_metrics_collector",
        return_value=fresh_collector,
    ):
        response = api_client.get("/api/v1/metrics")

    assert response.status_code == 200
    data = response.json()
    assert data["total_analyses"] == 0
    assert data["fallback_triggered"] == 0
    assert data["window_hours"] == 24


def test_metrics_endpoint_reflects_recorded_analyses(api_client: TestClient) -> None:
    """Los datos registrados deben verse reflejados en el endpoint."""
    collector = MetricsCollector()
    collector.record("connectivity", "high", fallback_triggered=True)
    collector.record("upstream", "high", fallback_triggered=False)
    collector.record("permissions", "medium", fallback_triggered=True)

    with patch(
        "sofia_ai_dataops.api.routes.metrics.get_metrics_collector",
        return_value=collector,
    ):
        response = api_client.get("/api/v1/metrics")

    assert response.status_code == 200
    data = response.json()
    assert data["total_analyses"] == 3
    assert data["by_failure_type"]["connectivity"] == 1
    assert data["by_failure_type"]["upstream"] == 1
    assert data["by_severity"]["high"] == 2
    assert data["fallback_triggered"] == 2


def test_metrics_endpoint_schema(api_client: TestClient) -> None:
    """La respuesta debe incluir todos los campos esperados del schema."""
    response = api_client.get("/api/v1/metrics")
    assert response.status_code == 200
    data = response.json()
    assert set(data.keys()) == {
        "total_analyses",
        "by_failure_type",
        "by_severity",
        "fallback_triggered",
        "window_hours",
    }
