"""Cliente de Qdrant para memoria semantica.

Objetivo: encapsular busquedas de incidentes similares sin acoplar LangGraph al motor vectorial.
"""

import hashlib
import math
import re
from uuid import UUID

from qdrant_client import QdrantClient
from qdrant_client.http import models

from sofia_ai_dataops.core.config import Settings
from sofia_ai_dataops.schemas.incidents import FailureType, IncidentAnalysisResponse

TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9_]+")


class IncidentVectorStore:
    def __init__(self, settings: Settings, client: QdrantClient | None = None) -> None:
        self._settings = settings
        self._client = client or QdrantClient(url=settings.qdrant_url)

    def search_similar(
        self,
        query: str,
        limit: int = 5,
        failure_type: FailureType | None = None,
    ) -> list[str]:
        try:
            self._ensure_collection()
            result = self._client.query_points(
                collection_name=self._settings.qdrant_collection,
                query=_embed_text(query, dimensions=self._settings.qdrant_vector_size),
                query_filter=_build_failure_type_filter(failure_type),
                limit=limit,
                with_payload=True,
            )
        except Exception:
            return []

        contexts: list[str] = []
        for point in result.points:
            payload = point.payload or {}
            contexts.append(_format_context(payload))
        return contexts

    def index_analysis(self, analysis: IncidentAnalysisResponse) -> None:
        try:
            self._ensure_collection()
            self._client.upsert(
                collection_name=self._settings.qdrant_collection,
                points=[
                    models.PointStruct(
                        id=_uuid_to_qdrant_id(analysis.analysis_id),
                        vector=_embed_text(
                            _analysis_to_document(analysis),
                            dimensions=self._settings.qdrant_vector_size,
                        ),
                        payload={
                            "analysis_id": str(analysis.analysis_id),
                            "dag_id": analysis.dag_id,
                            "task_id": analysis.task_id,
                            "run_id": analysis.run_id,
                            "failure_type": analysis.failure_type,
                            "severity": analysis.severity,
                            "summary": analysis.summary,
                            "root_cause": analysis.root_cause,
                            "recommendations": analysis.recommendations,
                            "source": analysis.source,
                            "created_at": analysis.created_at.isoformat(),
                        },
                    )
                ],
            )
        except Exception:
            return

    def count_indexed(self) -> int:
        try:
            if not self._client.collection_exists(self._settings.qdrant_collection):
                return 0
            result = self._client.count(
                collection_name=self._settings.qdrant_collection,
                exact=True,
            )
        except Exception:
            return 0

        return result.count

    def _ensure_collection(self) -> None:
        if self._client.collection_exists(self._settings.qdrant_collection):
            return

        self._client.create_collection(
            collection_name=self._settings.qdrant_collection,
            vectors_config=models.VectorParams(
                size=self._settings.qdrant_vector_size,
                distance=models.Distance.COSINE,
            ),
        )


def _embed_text(text: str, dimensions: int) -> list[float]:
    vector = [0.0] * dimensions
    for token in TOKEN_PATTERN.findall(text.lower()):
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % dimensions
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[index] += sign

    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]


def _analysis_to_document(analysis: IncidentAnalysisResponse) -> str:
    return "\n".join(
        [
            analysis.dag_id,
            analysis.task_id,
            analysis.run_id,
            analysis.failure_type,
            analysis.severity,
            analysis.summary,
            analysis.root_cause,
            " ".join(analysis.recommendations),
        ]
    )


def _format_context(payload: dict[str, object]) -> str:
    return (
        f"{payload.get('dag_id', 'unknown_dag')}.{payload.get('task_id', 'unknown_task')}: "
        f"{payload.get('failure_type', 'unknown')} / {payload.get('severity', 'unknown')} - "
        f"{payload.get('summary', 'No summary')}"
    )


def _uuid_to_qdrant_id(value: UUID) -> str:
    return str(value)


def _build_failure_type_filter(failure_type: FailureType | None) -> models.Filter | None:
    if failure_type is None or failure_type == "unknown":
        return None

    return models.Filter(
        must=[
            models.FieldCondition(
                key="failure_type",
                match=models.MatchValue(value=failure_type),
            )
        ]
    )
