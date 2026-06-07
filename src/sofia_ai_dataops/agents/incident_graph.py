"""Definicion del grafo de analisis de incidentes.

Objetivo: conectar nodos de recuperacion, clasificacion y recomendacion en un workflow LangGraph.
"""

from typing import Any, cast

from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph

from sofia_ai_dataops.agents.nodes.classify import make_classify_incident_node
from sofia_ai_dataops.agents.nodes.recommend import make_recommend_actions_node
from sofia_ai_dataops.agents.nodes.retrieve import make_retrieve_context_node
from sofia_ai_dataops.agents.state import IncidentGraphState
from sofia_ai_dataops.db.qdrant import IncidentVectorStore


def build_incident_graph(
    vector_store: IncidentVectorStore,
    chat_client: ChatOpenAI | None = None,
    llm_max_retries: int = 3,
) -> Any:
    graph = StateGraph(IncidentGraphState)

    graph.add_node("retrieve_context", cast(Any, make_retrieve_context_node(vector_store)))
    graph.add_node(
        "classify_incident",
        cast(Any, make_classify_incident_node(chat_client, max_retries=llm_max_retries)),
    )
    graph.add_node(
        "recommend_actions",
        cast(Any, make_recommend_actions_node(chat_client, max_retries=llm_max_retries)),
    )

    graph.set_entry_point("classify_incident")
    graph.add_edge("classify_incident", "retrieve_context")
    graph.add_edge("retrieve_context", "recommend_actions")
    graph.add_edge("recommend_actions", END)

    return graph.compile()
