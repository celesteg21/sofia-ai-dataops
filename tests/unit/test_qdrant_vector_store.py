"""Tests de memoria vectorial de incidentes.

Objetivo: validar que Sofia puede indexar incidentes y recuperar contexto similar desde Qdrant.
"""

from uuid import uuid4

from qdrant_client import QdrantClient

from sofia_ai_dataops.core.config import Settings
from sofia_ai_dataops.db.qdrant import IncidentVectorStore
from sofia_ai_dataops.schemas.incidents import IncidentAnalysisResponse


def test_vector_store_indexes_and_searches_similar_incidents() -> None:
    settings = Settings(
        qdrant_url="http://localhost:6333",
        qdrant_collection="test_airflow_incidents",
        qdrant_vector_size=64,
    )
    vector_store = IncidentVectorStore(
        settings=settings,
        client=QdrantClient(location=":memory:"),
    )
    analysis = IncidentAnalysisResponse(
        analysis_id=uuid4(),
        dag_id="daily_sales",
        task_id="load_warehouse",
        run_id="manual__test",
        failure_type="connectivity",
        severity="high",
        summary="Airflow task failed with likely connectivity issue.",
        root_cause="Database connection timed out.",
        recommendations=["Check database network reachability."],
        source="airflow",
    )

    vector_store.index_analysis(analysis)
    context = vector_store.search_similar(
        query="load_warehouse could not connect to database timeout",
        limit=1,
    )

    assert context == [
        "daily_sales.load_warehouse: connectivity / high - "
        "Airflow task failed with likely connectivity issue."
    ]


def test_vector_store_filters_similar_incidents_by_failure_type() -> None:
    settings = Settings(
        qdrant_url="http://localhost:6333",
        qdrant_collection="test_filtered_airflow_incidents",
        qdrant_vector_size=64,
    )
    vector_store = IncidentVectorStore(
        settings=settings,
        client=QdrantClient(location=":memory:"),
    )
    connectivity = IncidentAnalysisResponse(
        analysis_id=uuid4(),
        dag_id="daily_sales",
        task_id="load_warehouse",
        run_id="run-connectivity",
        failure_type="connectivity",
        severity="high",
        summary="Airflow task failed with likely connectivity issue.",
        root_cause="Database connection timed out.",
        recommendations=["Check database network reachability."],
        source="airflow",
    )
    permissions = IncidentAnalysisResponse(
        analysis_id=uuid4(),
        dag_id="daily_sales",
        task_id="read_secret",
        run_id="run-permissions",
        failure_type="permissions",
        severity="medium",
        summary="Airflow task failed with likely permissions issue.",
        root_cause="Secret backend denied access.",
        recommendations=["Check secret backend permissions."],
        source="airflow",
    )

    vector_store.index_analysis(connectivity)
    vector_store.index_analysis(permissions)
    context = vector_store.search_similar(
        query="load_warehouse could not connect to database timeout",
        limit=5,
        failure_type="connectivity",
    )

    assert context == [
        "daily_sales.load_warehouse: connectivity / high - "
        "Airflow task failed with likely connectivity issue."
    ]
