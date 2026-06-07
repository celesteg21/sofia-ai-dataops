"""Definicion del grafo de analisis de incidentes.

Objetivo: conectar nodos de recuperacion, clasificacion y recomendacion en un workflow LangGraph.
Cada nodo esta envuelto con instrumentacion de timing y eventos estructurados.
"""

import time
from collections.abc import Callable
from typing import Any, cast

from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph

from sofia_ai_dataops.agents.nodes.classify import make_classify_incident_node
from sofia_ai_dataops.agents.nodes.recommend import make_recommend_actions_node
from sofia_ai_dataops.agents.nodes.retrieve import make_retrieve_context_node
from sofia_ai_dataops.agents.state import IncidentGraphState
from sofia_ai_dataops.db.qdrant import IncidentVectorStore
from sofia_ai_dataops.observability.events import (
    log_node_completed,
    log_node_failed,
    log_node_started,
)


def _wrap_node(
    name: str,
    fn: Callable[[IncidentGraphState], IncidentGraphState],
) -> Callable[[IncidentGraphState], IncidentGraphState]:
    """Envuelve un nodo con logging de ciclo de vida y medicion de latencia."""

    def wrapped(state: IncidentGraphState) -> IncidentGraphState:
        dag_id = str(state.get("dag_id", ""))
        task_id = str(state.get("task_id", ""))
        log_node_started(name, dag_id, task_id)
        t0 = time.monotonic()
        try:
            result = fn(state)
            duration_ms = (time.monotonic() - t0) * 1000
            log_node_completed(
                name,
                dag_id,
                task_id,
                duration_ms,
                fallback_triggered=bool(result.get("fallback_triggered", False)),
            )
            return result
        except Exception:
            duration_ms = (time.monotonic() - t0) * 1000
            log_node_failed(name, dag_id, task_id, duration_ms)
            raise

    return wrapped


def build_incident_graph(
    vector_store: IncidentVectorStore,
    chat_client: ChatOpenAI | None = None,
    llm_max_retries: int = 3,
) -> Any:
    graph = StateGraph(IncidentGraphState)

    graph.add_node(
        "classify_incident",
        cast(
            Any,
            _wrap_node(
                "classify_incident",
                make_classify_incident_node(chat_client, max_retries=llm_max_retries),
            ),
        ),
    )
    graph.add_node(
        "retrieve_context",
        cast(Any, _wrap_node("retrieve_context", make_retrieve_context_node(vector_store))),
    )
    graph.add_node(
        "recommend_actions",
        cast(
            Any,
            _wrap_node(
                "recommend_actions",
                make_recommend_actions_node(chat_client, max_retries=llm_max_retries),
            ),
        ),
    )

    graph.set_entry_point("classify_incident")
    graph.add_edge("classify_incident", "retrieve_context")
    graph.add_edge("retrieve_context", "recommend_actions")
    graph.add_edge("recommend_actions", END)

    return graph.compile()
