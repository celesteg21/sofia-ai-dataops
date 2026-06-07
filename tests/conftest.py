"""Fixtures compartidos para tests de Sofia AI DataOps.

Objetivo: proveer infraestructura en-memoria reutilizable para tests unitarios e integración,
sin depender de Docker, PostgreSQL real ni OpenAI API key.
"""

from datetime import UTC, datetime

import pytest
from qdrant_client import QdrantClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from sofia_ai_dataops.agents.incident_graph import build_incident_graph
from sofia_ai_dataops.db.postgres import Base, IncidentAnalysisRepository
from sofia_ai_dataops.db.qdrant import IncidentVectorStore
from sofia_ai_dataops.schemas.airflow import AirflowTaskFailureEvent
from sofia_ai_dataops.schemas.incidents import IncidentAnalysisResponse
from sofia_ai_dataops.services.incident_service import IncidentAnalysisService

# ---------------------------------------------------------------------------
# Eventos Airflow — replican los DAGs del failure lab
# ---------------------------------------------------------------------------


@pytest.fixture
def db_timeout_event() -> AirflowTaskFailureEvent:
    """Replica sofia_lab_database_timeout: conexion al warehouse cae por timeout."""
    return AirflowTaskFailureEvent(
        dag_id="sofia_lab_database_timeout",
        task_id="query_warehouse",
        run_id="manual__2026-06-07T00:00:00+00:00",
        error=(
            "psycopg.OperationalError: connection to server at 'warehouse-postgres' (172.18.0.5)"
            " port 5432 failed: FATAL: could not connect to server."
            " Connection timed out after 30000ms."
        ),
        try_number=3,
        log_url="http://localhost:8080/dags/sofia_lab_database_timeout/grid",
        execution_date=datetime(2026, 6, 7, tzinfo=UTC),
        hostname="airflow-worker-1",
        operator="PythonOperator",
        metadata={"warehouse": "warehouse-postgres", "environment": "airflow-lab"},
    )


@pytest.fixture
def missing_credentials_event() -> AirflowTaskFailureEvent:
    """Replica sofia_lab_missing_credentials: secret backend niega acceso."""
    return AirflowTaskFailureEvent(
        dag_id="sofia_lab_missing_credentials",
        task_id="fetch_secret",
        run_id="manual__2026-06-07T01:00:00+00:00",
        error=(
            "airflow.exceptions.AirflowException: "
            "Error retrieving secret 'warehouse_conn' from backend: "
            "Access denied. Principal does not have permission to access secret."
        ),
        try_number=1,
        log_url="http://localhost:8080/dags/sofia_lab_missing_credentials/grid",
        execution_date=datetime(2026, 6, 7, 1, tzinfo=UTC),
        hostname="airflow-worker-1",
        operator="PythonOperator",
        metadata={"secret_key": "warehouse_conn", "environment": "airflow-lab"},
    )


@pytest.fixture
def upstream_failed_event() -> AirflowTaskFailureEvent:
    """Replica sofia_lab_upstream_failed: API externa devuelve 503."""
    return AirflowTaskFailureEvent(
        dag_id="sofia_lab_upstream_failed",
        task_id="extract_source",
        run_id="manual__2026-06-07T02:00:00+00:00",
        error="Upstream source API returned HTTP 503 Service Unavailable after 3 retries.",
        try_number=3,
        log_url="http://localhost:8080/dags/sofia_lab_upstream_failed/grid",
        execution_date=datetime(2026, 6, 7, 2, tzinfo=UTC),
        hostname="airflow-worker-2",
        operator="PythonOperator",
        metadata={
            "source_url": "https://api.datasource.internal/v1/orders",
            "environment": "airflow-lab",
        },
    )


@pytest.fixture
def causal_empty_ingestion_event() -> AirflowTaskFailureEvent:
    """Replica sofia_orders_ingest: fuente devuelve payload vacío."""
    return AirflowTaskFailureEvent(
        dag_id="sofia_orders_pipeline",
        task_id="ingest_raw_orders",
        run_id="scheduled__2026-06-07T00:00:00+00:00",
        error=(
            "Source API returned 200 OK but payload was empty. No rows were loaded."
            " Partition 2026-06-07 will be missing in raw_orders."
        ),
        try_number=1,
        log_url="http://localhost:8080/dags/sofia_orders_pipeline/grid",
        execution_date=datetime(2026, 6, 7, tzinfo=UTC),
        hostname="airflow-worker-1",
        operator="PythonOperator",
        metadata={
            "partition_date": "2026-06-07",
            "table": "raw_orders",
            "environment": "airflow-lab",
        },
    )


@pytest.fixture
def causal_missing_partition_event() -> AirflowTaskFailureEvent:
    """Replica sofia_orders_transform: falla porque falta la particion upstream."""
    return AirflowTaskFailureEvent(
        dag_id="sofia_orders_pipeline",
        task_id="transform_orders",
        run_id="scheduled__2026-06-07T00:00:00+00:00",
        error=(
            "AssertionError: Missing upstream partition."
            " raw_orders has no row for partition 2026-06-07."
            " Cannot proceed with transformation."
        ),
        try_number=1,
        log_url="http://localhost:8080/dags/sofia_orders_pipeline/grid",
        execution_date=datetime(2026, 6, 7, tzinfo=UTC),
        hostname="airflow-worker-1",
        operator="PythonOperator",
        metadata={
            "partition_date": "2026-06-07",
            "table": "staging_orders",
            "environment": "airflow-lab",
        },
    )


# ---------------------------------------------------------------------------
# Infraestructura en-memoria
# ---------------------------------------------------------------------------


@pytest.fixture
def in_memory_repository() -> IncidentAnalysisRepository:
    """Repositorio con SQLite en memoria, sin necesitar PostgreSQL real."""
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return IncidentAnalysisRepository(engine=engine)


@pytest.fixture
def in_memory_vector_store() -> IncidentVectorStore:
    """Vector store con QdrantClient en memoria, sin API de embeddings externos.

    Usa embeddings deterministicos (SHA-256) con vector size 64 para tests rapidos.
    """
    from sofia_ai_dataops.core.config import Settings

    settings = Settings(
        qdrant_url="http://localhost:6333",
        qdrant_collection="test_incidents",
        qdrant_vector_size=64,
    )
    return IncidentVectorStore(
        settings=settings,
        client=QdrantClient(location=":memory:"),
        embeddings_client=None,  # usa fallback deterministico
    )


@pytest.fixture
def seeded_vector_store(in_memory_vector_store: IncidentVectorStore) -> IncidentVectorStore:
    """Vector store pre-cargado con un incidente historico de conectividad."""
    from uuid import uuid4

    historical = IncidentAnalysisResponse(
        analysis_id=uuid4(),
        dag_id="sofia_lab_database_timeout",
        task_id="query_warehouse",
        run_id="manual__2026-06-01T00:00:00+00:00",
        failure_type="connectivity",
        severity="high",
        summary="Airflow task failed with likely connectivity issue.",
        root_cause="Warehouse PostgreSQL was unreachable. Network timeout after 30s.",
        recommendations=[
            "Check warehouse-postgres container health.",
            "Verify docker network connectivity between airflow-worker and warehouse-postgres.",
            "Review pg_hba.conf and connection pool limits.",
        ],
        source="airflow",
        metadata={"warehouse": "warehouse-postgres"},
    )
    in_memory_vector_store.index_analysis(historical)
    return in_memory_vector_store


@pytest.fixture
def incident_service(
    in_memory_repository: IncidentAnalysisRepository,
    in_memory_vector_store: IncidentVectorStore,
) -> IncidentAnalysisService:
    """Servicio completo con infraestructura en-memoria y sin LLM externo (keyword fallback)."""
    graph = build_incident_graph(
        vector_store=in_memory_vector_store,
        chat_client=None,  # usa keyword fallback — sin OpenAI API key en CI
    )
    return IncidentAnalysisService(
        graph=graph,
        repository=in_memory_repository,
        vector_store=in_memory_vector_store,
    )


@pytest.fixture
def seeded_incident_service(
    in_memory_repository: IncidentAnalysisRepository,
    seeded_vector_store: IncidentVectorStore,
) -> IncidentAnalysisService:
    """Servicio con historial pre-cargado en Qdrant para probar recuperacion de memoria."""
    graph = build_incident_graph(
        vector_store=seeded_vector_store,
        chat_client=None,
    )
    return IncidentAnalysisService(
        graph=graph,
        repository=in_memory_repository,
        vector_store=seeded_vector_store,
    )
