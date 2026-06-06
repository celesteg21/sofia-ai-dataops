"""Nodo de recuperacion de contexto.

Objetivo: buscar incidentes similares o conocimiento historico para enriquecer el diagnostico.
"""

from collections.abc import Callable

from sofia_ai_dataops.agents.state import IncidentGraphState
from sofia_ai_dataops.db.qdrant import IncidentVectorStore


def make_retrieve_context_node(
    vector_store: IncidentVectorStore,
) -> Callable[[IncidentGraphState], IncidentGraphState]:
    def retrieve_context(state: IncidentGraphState) -> IncidentGraphState:
        query = "\n".join(
            [
                f"dag_id={state.get('dag_id', '')}",
                f"task_id={state.get('task_id', '')}",
                f"failure_type={state.get('failure_type', '')}",
                state.get("logs", ""),
            ]
        )
        context = vector_store.search_similar(
            query=query,
            limit=5,
            failure_type=state.get("failure_type"),
        )
        return {**state, "retrieved_context": context}

    return retrieve_context
