#!/usr/bin/env python
"""Simulacion end-to-end del pipeline de Sofia AI DataOps.

Demuestra el flujo completo desde un evento Airflow hasta el diagnostico persistido,
incluyendo recuperacion de memoria en el segundo incidente identico.

Uso:
    python scripts/simulate_dag_failure.py

No requiere Docker ni OpenAI API key — usa infraestructura en-memoria.
"""

import asyncio
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

# agregar src/ al path para poder importar el paquete sin instalar
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from qdrant_client import QdrantClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from sofia_ai_dataops.agents.incident_graph import build_incident_graph
from sofia_ai_dataops.db.postgres import Base, IncidentAnalysisRepository
from sofia_ai_dataops.db.qdrant import IncidentVectorStore
from sofia_ai_dataops.ingestion.airflow import airflow_failure_to_incident
from sofia_ai_dataops.schemas.airflow import AirflowTaskFailureEvent
from sofia_ai_dataops.schemas.incidents import IncidentAnalysisResponse
from sofia_ai_dataops.services.incident_service import IncidentAnalysisService

# ---------------------------------------------------------------------------
# Helpers de presentacion
# ---------------------------------------------------------------------------

RESET = "\033[0m"
BOLD = "\033[1m"
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
MAGENTA = "\033[95m"
DIM = "\033[2m"


def _step(tag: str, msg: str, color: str = CYAN) -> None:
    ts = datetime.now(UTC).strftime("%H:%M:%S.%f")[:-3]
    print(f"{DIM}{ts}{RESET}  {color}{BOLD}[{tag}]{RESET}  {msg}")


def _json(label: str, data: dict[str, Any]) -> None:
    formatted = json.dumps(data, indent=2, default=str, ensure_ascii=False)
    lines = formatted.split("\n")
    print(f"  {DIM}{label}:{RESET}")
    for line in lines:
        print(f"    {DIM}{line}{RESET}")


def _divider(title: str = "") -> None:
    width = 72
    if title:
        pad = (width - len(title) - 2) // 2
        print(f"\n{DIM}{'─' * pad} {BOLD}{title}{RESET}{DIM} {'─' * pad}{RESET}\n")
    else:
        print(f"\n{DIM}{'─' * width}{RESET}\n")


def _severity_color(severity: str) -> str:
    return {
        "critical": RED,
        "high": YELLOW,
        "medium": MAGENTA,
        "low": GREEN,
    }.get(severity, RESET)


# ---------------------------------------------------------------------------
# Infraestructura en-memoria
# ---------------------------------------------------------------------------


def _build_in_memory_service() -> tuple[IncidentAnalysisService, IncidentVectorStore]:
    from sofia_ai_dataops.core.config import Settings

    settings = Settings(
        qdrant_url="http://localhost:6333",
        qdrant_collection="sim_incidents",
        qdrant_vector_size=64,
    )

    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    repository = IncidentAnalysisRepository(engine=engine)

    qdrant = QdrantClient(location=":memory:")
    vector_store = IncidentVectorStore(
        settings=settings,
        client=qdrant,
        embeddings_client=None,  # modo deterministico, sin API key
    )

    graph = build_incident_graph(vector_store=vector_store, chat_client=None)
    service = IncidentAnalysisService(
        graph=graph,
        repository=repository,
        vector_store=vector_store,
    )
    return service, vector_store


# ---------------------------------------------------------------------------
# Escenarios del lab
# ---------------------------------------------------------------------------

SCENARIOS: list[dict[str, Any]] = [
    {
        "name": "DB Timeout (sofia_lab_database_timeout)",
        "event": AirflowTaskFailureEvent(
            dag_id="sofia_lab_database_timeout",
            task_id="query_warehouse",
            run_id="manual__2026-06-07T10:00:00+00:00",
            error=(
                "psycopg.OperationalError: connection to server at 'warehouse-postgres' "
                "(172.18.0.5) port 5432 failed: FATAL: could not connect to server. "
                "Connection timed out after 30000ms."
            ),
            try_number=3,
            log_url="http://localhost:8080/dags/sofia_lab_database_timeout/grid",
            execution_date=datetime(2026, 6, 7, 10, 0, tzinfo=UTC),
            hostname="airflow-worker-1",
            operator="PythonOperator",
            metadata={"warehouse": "warehouse-postgres", "environment": "airflow-lab"},
        ),
        "expected_failure_type": "connectivity",
        "expected_severity": "high",
    },
    {
        "name": "Missing Credentials (sofia_lab_missing_credentials)",
        "event": AirflowTaskFailureEvent(
            dag_id="sofia_lab_missing_credentials",
            task_id="fetch_secret",
            run_id="manual__2026-06-07T10:05:00+00:00",
            error=(
                "airflow.exceptions.AirflowException: Error retrieving secret 'warehouse_conn' "
                "from backend: Access denied. Principal does not have permission to access secret."
            ),
            try_number=1,
            log_url="http://localhost:8080/dags/sofia_lab_missing_credentials/grid",
            execution_date=datetime(2026, 6, 7, 10, 5, tzinfo=UTC),
            hostname="airflow-worker-1",
            operator="PythonOperator",
            metadata={"secret_key": "warehouse_conn", "environment": "airflow-lab"},
        ),
        "expected_failure_type": "permissions",
        "expected_severity": "medium",
    },
    {
        "name": "Upstream 503 (sofia_lab_upstream_failed)",
        "event": AirflowTaskFailureEvent(
            dag_id="sofia_lab_upstream_failed",
            task_id="extract_source",
            run_id="manual__2026-06-07T10:10:00+00:00",
            error="Upstream source API returned HTTP 503 Service Unavailable after 3 retries.",
            try_number=3,
            log_url="http://localhost:8080/dags/sofia_lab_upstream_failed/grid",
            execution_date=datetime(2026, 6, 7, 10, 10, tzinfo=UTC),
            hostname="airflow-worker-2",
            operator="PythonOperator",
            metadata={
                "source_url": "https://api.datasource.internal/v1/orders",
                "environment": "airflow-lab",
            },
        ),
        "expected_failure_type": "upstream",
        "expected_severity": "high",
    },
    {
        "name": "Causal — Ingesta vacía (sofia_orders_ingest)",
        "event": AirflowTaskFailureEvent(
            dag_id="sofia_orders_pipeline",
            task_id="ingest_raw_orders",
            run_id="scheduled__2026-06-07T00:00:00+00:00",
            error=(
                "Source API returned 200 OK but payload was empty. "
                "No rows were loaded. Partition 2026-06-07 will be missing in raw_orders."
            ),
            try_number=1,
            log_url="http://localhost:8080/dags/sofia_orders_pipeline/grid",
            execution_date=datetime(2026, 6, 7, tzinfo=UTC),
            hostname="airflow-worker-1",
            operator="PythonOperator",
            metadata={"partition_date": "2026-06-07", "table": "raw_orders"},
        ),
        "expected_failure_type": "upstream",
        "expected_severity": "high",
    },
    {
        "name": "Causal — Partición faltante (sofia_orders_transform)",
        "event": AirflowTaskFailureEvent(
            dag_id="sofia_orders_pipeline",
            task_id="transform_orders",
            run_id="scheduled__2026-06-07T00:00:00+00:00",
            error=(
                "AssertionError: Missing upstream partition. "
                "raw_orders has no row for partition 2026-06-07. "
                "Cannot proceed with transformation."
            ),
            try_number=1,
            log_url="http://localhost:8080/dags/sofia_orders_pipeline/grid",
            execution_date=datetime(2026, 6, 7, tzinfo=UTC),
            hostname="airflow-worker-1",
            operator="PythonOperator",
            metadata={"partition_date": "2026-06-07", "table": "staging_orders"},
        ),
        "expected_failure_type": "upstream",
        "expected_severity": "high",
    },
]


# ---------------------------------------------------------------------------
# Simulacion
# ---------------------------------------------------------------------------


async def simulate_scenario(
    service: IncidentAnalysisService,
    scenario: dict[str, Any],
    index: int,
    total: int,
) -> IncidentAnalysisResponse:
    event: AirflowTaskFailureEvent = scenario["event"]
    name: str = scenario["name"]
    expected_type: str = scenario["expected_failure_type"]
    expected_sev: str = scenario["expected_severity"]

    _divider(f"Escenario {index}/{total}: {name}")

    # --- Deteccion ---
    _step("DETECCIÓN", f"Evento Airflow recibido via callback on_task_instance_failed")
    _json(
        "payload",
        {
            "dag_id": event.dag_id,
            "task_id": event.task_id,
            "run_id": event.run_id,
            "try_number": event.try_number,
            "hostname": event.hostname,
            "error": event.error[:120] + ("..." if len(event.error) > 120 else ""),
        },
    )

    # --- Normalizacion ---
    print()
    _step("NORMALIZACIÓN", "AirflowTaskFailureEvent → IncidentAnalysisRequest")
    t0 = time.perf_counter()
    incident = airflow_failure_to_incident(event)
    norm_ms = (time.perf_counter() - t0) * 1000
    _json(
        "resultado",
        {
            "source": incident.source,
            "logs": incident.logs[:200] + "...",
            "metadata_keys": list(incident.metadata.keys()),
        },
    )
    print(f"  {DIM}→ {norm_ms:.1f}ms{RESET}")

    # --- Grafo LangGraph ---
    print()
    _step("GRAFO", "Ejecutando LangGraph: classify → retrieve → recommend", MAGENTA)
    _step("GRAFO/nodo 1", "classify_incident  (modo: keyword-fallback, sin OPENAI_API_KEY)", DIM)

    t0 = time.perf_counter()
    analysis = await service.analyze(incident)
    graph_ms = (time.perf_counter() - t0) * 1000

    sev_color = _severity_color(analysis.severity)
    _step(
        "GRAFO/nodo 1",
        f"→ failure_type: {BOLD}{analysis.failure_type}{RESET}  "
        f"severity: {sev_color}{BOLD}{analysis.severity}{RESET}",
        DIM,
    )
    _step(
        "GRAFO/nodo 2",
        f"retrieve_context  → {len(analysis.retrieved_context)} incidentes similares en Qdrant",
        DIM,
    )
    if analysis.retrieved_context:
        for ctx in analysis.retrieved_context:
            print(f"    {DIM}• {ctx[:100]}{RESET}")
    _step(
        "GRAFO/nodo 3",
        f"recommend_actions  → {len(analysis.recommendations)} recomendaciones generadas",
        DIM,
    )
    print(f"  {DIM}→ grafo completo en {graph_ms:.1f}ms{RESET}")

    # --- Resultado completo ---
    print()
    _step("RESULTADO", "Diagnóstico final", GREEN)
    _json(
        "analysis",
        {
            "analysis_id": str(analysis.analysis_id),
            "dag_id": analysis.dag_id,
            "task_id": analysis.task_id,
            "failure_type": analysis.failure_type,
            "severity": analysis.severity,
            "summary": analysis.summary,
            "root_cause": analysis.root_cause,
            "recommendations": analysis.recommendations,
            "retrieved_context": analysis.retrieved_context,
            "source": analysis.source,
            "created_at": analysis.created_at.isoformat(),
        },
    )

    # --- Persistencia ---
    persisted = service.get_analysis(analysis.analysis_id)
    assert persisted is not None
    _step("PERSISTENCIA", f"Guardado en SQLite  analysis_id={analysis.analysis_id}", DIM)

    # --- Memoria vectorial ---
    _step("MEMORIA", "Indexado en Qdrant (embeddings deterministicos)", DIM)

    # --- Validacion de expectativas ---
    print()
    ok_type = analysis.failure_type == expected_type
    ok_sev = analysis.severity == expected_sev
    type_icon = f"{GREEN}✓{RESET}" if ok_type else f"{RED}✗{RESET}"
    sev_icon = f"{GREEN}✓{RESET}" if ok_sev else f"{RED}✗{RESET}"
    print(
        f"  {type_icon} failure_type: {BOLD}{analysis.failure_type}{RESET}"
        f"  (esperado: {expected_type})"
    )
    print(
        f"  {sev_icon} severity:     {BOLD}{analysis.severity}{RESET}"
        f"  (esperado: {expected_sev})"
    )

    if not ok_type or not ok_sev:
        print(f"\n  {RED}{BOLD}FALLA en escenario: {name}{RESET}")

    return analysis


async def main() -> None:
    print(f"\n{BOLD}{CYAN}Sofia AI DataOps — Simulación End-to-End{RESET}")
    print(f"{DIM}Infraestructura: SQLite en-memoria + Qdrant en-memoria{RESET}")
    print(f"{DIM}LLM: keyword-fallback (sin OPENAI_API_KEY){RESET}")

    service, vector_store = _build_in_memory_service()
    _step("INIT", "Infraestructura en-memoria lista", GREEN)

    total = len(SCENARIOS)
    analyses: list[IncidentAnalysisResponse] = []

    for i, scenario in enumerate(SCENARIOS, 1):
        analysis = await simulate_scenario(service, scenario, i, total)
        analyses.append(analysis)

    # --- Demo de memoria: segundo incidente identico recupera contexto ---
    _divider("Demo de Memoria: Segundo Incidente Idéntico")
    _step("MEMORIA", "Analizando SEGUNDA falla identica de DB timeout...")

    repeat_event = SCENARIOS[0]["event"]
    repeat_incident = airflow_failure_to_incident(repeat_event)  # type: ignore[arg-type]
    repeat_analysis = await service.analyze(repeat_incident)

    print()
    if repeat_analysis.retrieved_context:
        _step(
            "RECUPERACIÓN",
            f"{GREEN}{BOLD}{len(repeat_analysis.retrieved_context)} incidente(s) similar(es) encontrado(s) en memoria:{RESET}",
            GREEN,
        )
        for ctx in repeat_analysis.retrieved_context:
            print(f"  {GREEN}• {ctx}{RESET}")
    else:
        _step("RECUPERACIÓN", f"{YELLOW}Sin contexto recuperado (embeddings deterministicos pueden no matchear){RESET}")

    # --- Resumen ---
    _divider("Resumen")
    all_analyses = service.list_recent_analyses(limit=20)
    _step("TOTAL", f"{len(all_analyses)} análisis procesados y persistidos", GREEN)

    by_type: dict[str, int] = {}
    by_sev: dict[str, int] = {}
    for a in all_analyses:
        by_type[a.failure_type] = by_type.get(a.failure_type, 0) + 1
        by_sev[a.severity] = by_sev.get(a.severity, 0) + 1

    print(f"\n  {BOLD}Por tipo de falla:{RESET}")
    for ft, count in sorted(by_type.items()):
        print(f"    {count:2d}x  {ft}")
    print(f"\n  {BOLD}Por severidad:{RESET}")
    for sev, count in sorted(by_sev.items(), key=lambda x: ["critical", "high", "medium", "low"].index(x[0]) if x[0] in ["critical", "high", "medium", "low"] else 99):
        color = _severity_color(sev)
        print(f"    {count:2d}x  {color}{sev}{RESET}")

    # validar que todos los escenarios pasaron
    failed = [
        s["name"]
        for s, a in zip(SCENARIOS, analyses)
        if a.failure_type != s["expected_failure_type"] or a.severity != s["expected_severity"]
    ]
    print()
    if failed:
        _step("RESULTADO", f"{RED}{BOLD}FALLARON {len(failed)} escenarios: {failed}{RESET}", RED)
        sys.exit(1)
    else:
        _step(
            "RESULTADO",
            f"{GREEN}{BOLD}Todos los escenarios clasificados correctamente ✓{RESET}",
            GREEN,
        )


if __name__ == "__main__":
    asyncio.run(main())
