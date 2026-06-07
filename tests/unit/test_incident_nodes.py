"""Tests unitarios de nodos del agente.

Objetivo: verificar reglas de clasificacion y recomendaciones, tanto con keyword fallback
como con el path de LLM (usando un cliente mockeado).
"""

from typing import cast
from unittest.mock import MagicMock

import pytest
from langchain_openai import ChatOpenAI

from sofia_ai_dataops.agents.incident_graph import build_incident_graph
from sofia_ai_dataops.agents.nodes.classify import (
    classify_incident,
    make_classify_incident_node,
)
from sofia_ai_dataops.agents.nodes.recommend import (
    make_recommend_actions_node,
    recommend_actions,
)
from sofia_ai_dataops.db.qdrant import IncidentVectorStore
from sofia_ai_dataops.schemas.incidents import FailureType


class FakeVectorStore:
    def search_similar(
        self,
        query: str,
        limit: int = 5,
        failure_type: FailureType | None = None,
    ) -> list[str]:
        _ = query, limit, failure_type
        return ["Previous incident: database connection timeout fixed by checking networking."]


# --- Tests de keyword fallback (sin LLM) ---


def test_classifies_connectivity_incident() -> None:
    state = classify_incident({"logs": "could not connect to server: timeout"})

    assert state["failure_type"] == "connectivity"
    assert state["severity"] == "high"


def test_classifies_empty_ingestion_as_upstream_incident() -> None:
    state = classify_incident(
        {"logs": "Source API returned 200 OK but payload was empty. No rows were loaded."}
    )

    assert state["failure_type"] == "upstream"
    assert state["severity"] == "high"


def test_recommends_actions_for_permissions_incident() -> None:
    state = recommend_actions({"failure_type": "permissions", "retrieved_context": []})

    assert "secret backend" in " ".join(state["recommendations"])


# --- Tests con cliente LLM mockeado ---


def _make_mock_chat_client(failure_type: str, severity: str, summary: str) -> ChatOpenAI:
    """Construye un ChatOpenAI mock que devuelve una clasificacion predefinida."""
    from pydantic import BaseModel

    class FakeOutput(BaseModel):
        failure_type: str
        severity: str
        summary: str

    output = FakeOutput(failure_type=failure_type, severity=severity, summary=summary)
    structured_mock = MagicMock()
    structured_mock.invoke.return_value = output

    client = MagicMock(spec=ChatOpenAI)
    client.with_structured_output.return_value = structured_mock
    return cast(ChatOpenAI, client)


def test_classify_node_uses_llm_output_when_available() -> None:
    mock_client = _make_mock_chat_client(
        failure_type="permissions",
        severity="critical",
        summary="Missing IAM role on Airflow worker.",
    )
    classify = make_classify_incident_node(chat_client=mock_client)

    state = classify({"logs": "could not connect to server: timeout", "dag_id": "test"})

    # El LLM override el keyword matching
    assert state["failure_type"] == "permissions"
    assert state["severity"] == "critical"
    assert state["summary"] == "Missing IAM role on Airflow worker."


def test_classify_node_falls_back_to_keywords_on_llm_error() -> None:
    client = MagicMock(spec=ChatOpenAI)
    client.with_structured_output.side_effect = RuntimeError("API unavailable")
    classify = make_classify_incident_node(chat_client=cast(ChatOpenAI, client))

    state = classify({"logs": "could not connect to server: timeout"})

    # Fallback a keywords
    assert state["failure_type"] == "connectivity"
    assert state["severity"] == "high"


def test_recommend_node_uses_llm_output_when_available() -> None:
    from pydantic import BaseModel

    class FakeRecommendOutput(BaseModel):
        root_cause: str
        recommendations: list[str]

    output = FakeRecommendOutput(
        root_cause="VPC security group blocks outbound traffic on port 5432.",
        recommendations=["Open port 5432 in the worker security group.", "Verify RDS endpoint."],
    )
    structured_mock = MagicMock()
    structured_mock.invoke.return_value = output

    client = MagicMock(spec=ChatOpenAI)
    client.with_structured_output.return_value = structured_mock
    recommend = make_recommend_actions_node(chat_client=cast(ChatOpenAI, client))

    state = recommend({"failure_type": "connectivity", "retrieved_context": []})

    assert "port 5432" in state["root_cause"]
    assert len(state["recommendations"]) == 2


def test_recommend_node_falls_back_to_defaults_on_llm_error() -> None:
    client = MagicMock(spec=ChatOpenAI)
    client.with_structured_output.side_effect = RuntimeError("API unavailable")
    recommend = make_recommend_actions_node(chat_client=cast(ChatOpenAI, client))

    state = recommend({"failure_type": "connectivity", "retrieved_context": []})

    assert state["recommendations"]
    assert "network" in " ".join(state["recommendations"]).lower()


# --- Test del grafo completo ---


@pytest.mark.asyncio
async def test_incident_graph_compiles_and_runs() -> None:
    vector_store = cast(IncidentVectorStore, FakeVectorStore())
    graph = build_incident_graph(vector_store=vector_store)

    result = await graph.ainvoke(
        {
            "dag_id": "daily_sales",
            "task_id": "load_warehouse",
            "run_id": "manual__2026-06-04T00:00:00+00:00",
            "logs": "could not connect to server: timeout",
            "metadata": {"owner": "data-platform"},
        }
    )

    assert result["retrieved_context"] == [
        "Previous incident: database connection timeout fixed by checking networking."
    ]
    assert result["failure_type"] == "connectivity"
    assert result["severity"] == "high"
    assert result["summary"]
    assert result["root_cause"]
    assert result["recommendations"]
