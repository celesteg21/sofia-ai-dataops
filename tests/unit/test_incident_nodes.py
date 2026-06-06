"""Tests unitarios de nodos del agente.

Objetivo: verificar reglas iniciales de clasificacion y recomendaciones sin depender de
servicios externos.
"""

from typing import cast

from sofia_ai_dataops.agents.incident_graph import build_incident_graph
from sofia_ai_dataops.agents.nodes.classify import classify_incident
from sofia_ai_dataops.agents.nodes.recommend import recommend_actions
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


def test_classifies_connectivity_incident() -> None:
    state = classify_incident({"logs": "could not connect to server: timeout"})

    assert state["failure_type"] == "connectivity"
    assert state["severity"] == "high"


def test_recommends_actions_for_permissions_incident() -> None:
    state = recommend_actions({"failure_type": "permissions", "retrieved_context": []})

    assert "secret backend" in " ".join(state["recommendations"])


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
