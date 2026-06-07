"""Contadores en memoria de metricas operacionales de Sofia.

Objetivo: mantener un snapshot de ultimas 24h (total, por tipo, por severidad, fallbacks)
sin nueva tabla de base de datos. Se resetea al reiniciar el proceso.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from threading import Lock
from typing import TypedDict

import structlog

_log = structlog.get_logger(__name__)

_WINDOW_HOURS = 24


@dataclass
class _Entry:
    failure_type: str
    severity: str
    fallback_triggered: bool
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class MetricsSnapshot(TypedDict):
    total_analyses: int
    by_failure_type: dict[str, int]
    by_severity: dict[str, int]
    fallback_triggered: int
    window_hours: int


class MetricsCollector:
    """Colector thread-safe de metricas en memoria para las ultimas 24h."""

    def __init__(self) -> None:
        self._entries: list[_Entry] = []
        self._lock = Lock()

    def record(self, failure_type: str, severity: str, fallback_triggered: bool) -> None:
        """Registra un analisis completado."""
        with self._lock:
            self._entries.append(
                _Entry(
                    failure_type=failure_type,
                    severity=severity,
                    fallback_triggered=fallback_triggered,
                )
            )

    def snapshot(self) -> MetricsSnapshot:
        """Devuelve un snapshot de metricas de las ultimas 24h y descarta entradas antiguas."""
        cutoff = datetime.now(UTC) - timedelta(hours=_WINDOW_HOURS)
        with self._lock:
            recent = [e for e in self._entries if e.created_at >= cutoff]
            self._entries = recent  # elimina entradas fuera de ventana

        by_failure_type: dict[str, int] = defaultdict(int)
        by_severity: dict[str, int] = defaultdict(int)
        fallback_count = 0

        for entry in recent:
            by_failure_type[entry.failure_type] += 1
            by_severity[entry.severity] += 1
            if entry.fallback_triggered:
                fallback_count += 1

        return MetricsSnapshot(
            total_analyses=len(recent),
            by_failure_type=dict(by_failure_type),
            by_severity=dict(by_severity),
            fallback_triggered=fallback_count,
            window_hours=_WINDOW_HOURS,
        )


# Singleton del proceso — compartido entre todos los requests HTTP.
_collector = MetricsCollector()


def get_metrics_collector() -> MetricsCollector:
    """Devuelve el colector global de metricas."""
    return _collector
