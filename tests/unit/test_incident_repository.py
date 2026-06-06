"""Tests del repositorio de analisis de incidentes.

Objetivo: validar que la capa de persistencia guarda y recupera diagnosticos sin depender de
PostgreSQL real durante los tests unitarios.
"""

from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from sofia_ai_dataops.db.postgres import Base, IncidentAnalysisRepository
from sofia_ai_dataops.schemas.incidents import IncidentAnalysisResponse


def test_repository_saves_and_fetches_analysis() -> None:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    repository = IncidentAnalysisRepository(engine=engine)
    analysis = IncidentAnalysisResponse(
        analysis_id=uuid4(),
        dag_id="daily_sales",
        task_id="load_warehouse",
        run_id="manual__2026-06-04T00:00:00+00:00",
        failure_type="connectivity",
        severity="high",
        summary="Database connection timed out.",
        root_cause="Warehouse database was unavailable.",
        recommendations=["Check network path", "Review database availability"],
        metadata={"owner": "data-platform"},
        retrieved_context=["Similar timeout incident"],
        source="airflow",
    )

    repository.save(analysis)

    fetched = repository.get(analysis.analysis_id)
    assert fetched is not None
    assert fetched.analysis_id == analysis.analysis_id
    assert fetched.failure_type == analysis.failure_type
    assert fetched.severity == analysis.severity
    assert fetched.metadata == analysis.metadata
    assert fetched.retrieved_context == analysis.retrieved_context
    assert fetched.source == analysis.source


def test_repository_lists_recent_analyses() -> None:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    repository = IncidentAnalysisRepository(engine=engine)
    first = IncidentAnalysisResponse(
        analysis_id=uuid4(),
        dag_id="daily_sales",
        task_id="extract",
        run_id="run-1",
        failure_type="unknown",
        severity="medium",
        summary="Task failed.",
        root_cause="Unknown at this stage.",
        recommendations=["Inspect logs"],
    )
    second = IncidentAnalysisResponse(
        analysis_id=uuid4(),
        dag_id="daily_sales",
        task_id="load",
        run_id="run-2",
        failure_type="connectivity",
        severity="critical",
        summary="Warehouse load failed.",
        root_cause="Database unavailable.",
        recommendations=["Check database"],
    )

    repository.save(first)
    repository.save(second)

    analyses = repository.list_recent(limit=10)
    assert {analysis.analysis_id for analysis in analyses} == {
        first.analysis_id,
        second.analysis_id,
    }
    assert repository.count() == 2
