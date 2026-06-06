"""Persistencia de analisis en PostgreSQL.

Objetivo: guardar los diagnosticos generados para auditoria, historial y analisis futuros.
"""

from datetime import datetime
from typing import Any, cast
from uuid import UUID

from sqlalchemy import JSON, DateTime, Engine, String, Uuid, create_engine, func, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from sofia_ai_dataops.core.config import Settings
from sofia_ai_dataops.schemas.incidents import FailureType, IncidentAnalysisResponse, Severity


class Base(DeclarativeBase):
    pass


class IncidentAnalysisRecord(Base):
    __tablename__ = "incident_analyses"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    dag_id: Mapped[str] = mapped_column(String, nullable=False)
    task_id: Mapped[str] = mapped_column(String, nullable=False)
    run_id: Mapped[str] = mapped_column(String, nullable=False)
    failure_type: Mapped[str] = mapped_column(String, nullable=False)
    severity: Mapped[str] = mapped_column(String, nullable=False)
    summary: Mapped[str] = mapped_column(String, nullable=False)
    root_cause: Mapped[str | None] = mapped_column(String, nullable=True)
    recommendations: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    event_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False)
    retrieved_context: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False, default="manual")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class IncidentAnalysisRepository:
    def __init__(self, settings: Settings | None = None, engine: Engine | None = None) -> None:
        if engine is None:
            if settings is None:
                msg = "settings or engine must be provided"
                raise ValueError(msg)
            engine = create_engine(settings.postgres_dsn, pool_pre_ping=True)

        self._engine = engine
        self._session_factory = sessionmaker(self._engine, expire_on_commit=False)

    def save(self, analysis: IncidentAnalysisResponse) -> None:
        record = IncidentAnalysisRecord(
            id=analysis.analysis_id,
            dag_id=analysis.dag_id,
            task_id=analysis.task_id,
            run_id=analysis.run_id,
            failure_type=analysis.failure_type,
            severity=analysis.severity,
            summary=analysis.summary,
            root_cause=analysis.root_cause,
            recommendations=analysis.recommendations,
            event_metadata=analysis.metadata,
            retrieved_context=analysis.retrieved_context,
            source=analysis.source,
            created_at=analysis.created_at,
        )
        with self._session_factory() as session:
            session.add(record)
            session.commit()

    def get(self, analysis_id: UUID) -> IncidentAnalysisResponse | None:
        with self._session_factory() as session:
            record = session.get(IncidentAnalysisRecord, analysis_id)
            if record is None:
                return None
            return _record_to_response(record)

    def list_recent(self, limit: int = 20) -> list[IncidentAnalysisResponse]:
        statement = (
            select(IncidentAnalysisRecord)
            .order_by(IncidentAnalysisRecord.created_at.desc())
            .limit(limit)
        )
        with self._session_factory() as session:
            return [_record_to_response(record) for record in session.scalars(statement)]

    def count(self) -> int:
        statement = select(func.count()).select_from(IncidentAnalysisRecord)
        with self._session_factory() as session:
            return session.scalar(statement) or 0


def _record_to_response(record: IncidentAnalysisRecord) -> IncidentAnalysisResponse:
    recommendations: Any = record.recommendations
    retrieved_context: Any = record.retrieved_context
    return IncidentAnalysisResponse(
        analysis_id=record.id,
        dag_id=record.dag_id,
        task_id=record.task_id,
        run_id=record.run_id,
        failure_type=cast(FailureType, record.failure_type),
        severity=cast(Severity, record.severity),
        summary=record.summary,
        root_cause=record.root_cause or "",
        recommendations=list(recommendations),
        metadata=record.event_metadata,
        retrieved_context=list(retrieved_context),
        source=record.source,
        created_at=record.created_at,
    )
