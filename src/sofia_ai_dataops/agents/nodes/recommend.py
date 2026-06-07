"""Nodo de recomendacion de acciones.

Objetivo: generar causa raiz y pasos de remediacion usando LLM cuando esta disponible,
con fallback a listas predefinidas por tipo de falla.
"""

from collections.abc import Callable

import structlog
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from sofia_ai_dataops.agents.prompts import recommend_v1
from sofia_ai_dataops.agents.state import IncidentGraphState

_log = structlog.get_logger(__name__)

_RECOMMENDATIONS_BY_TYPE: dict[str, list[str]] = {
    "connectivity": [
        "Check database or service network reachability from the Airflow worker.",
        "Validate credentials, DNS resolution, firewall rules, and connection pool limits.",
        "Retry the task after confirming the downstream dependency is healthy.",
    ],
    "permissions": [
        "Verify the Airflow connection user and secret backend value.",
        "Confirm the task has access to the target dataset, bucket, or service account.",
    ],
    "infrastructure": [
        "Inspect worker disk, memory, and scheduler health.",
        "Scale or recycle unhealthy workers before retrying the DAG run.",
    ],
    "upstream": [
        "Check the upstream service health, status page, and recent deploys.",
        "Retry only after confirming the dependency is available again.",
        "Consider adding backoff, retries, or circuit-breaker behavior for this dependency.",
    ],
    "unknown": [
        "Inspect the complete task log around the first exception.",
        "Compare with recent DAG, dependency, and environment changes.",
    ],
}


class _RecommendationOutput(BaseModel):
    root_cause: str
    recommendations: list[str]


def make_recommend_actions_node(
    chat_client: ChatOpenAI | None = None,
) -> Callable[[IncidentGraphState], IncidentGraphState]:
    """Construye el nodo de recomendaciones con o sin LLM."""

    def recommend_actions(state: IncidentGraphState) -> IncidentGraphState:
        if chat_client is not None:
            try:
                return _recommend_with_llm(chat_client, state)
            except Exception:
                _log.warning("llm_recommend_fallback", exc_info=True)
        return _recommend_with_defaults(state)

    return recommend_actions


def _recommend_with_llm(
    chat_client: ChatOpenAI,
    state: IncidentGraphState,
) -> IncidentGraphState:
    from sofia_ai_dataops.agents.llm import llm_retry

    structured_llm = chat_client.with_structured_output(_RecommendationOutput)

    @llm_retry
    def _invoke() -> _RecommendationOutput:
        return structured_llm.invoke(  # type: ignore[return-value]
            [
                SystemMessage(content=recommend_v1.SYSTEM),
                HumanMessage(content=recommend_v1.build_prompt(state)),
            ]
        )

    output = _invoke()
    return {
        **state,
        "root_cause": output.root_cause,
        "recommendations": output.recommendations,
    }


def _recommend_with_defaults(state: IncidentGraphState) -> IncidentGraphState:
    failure_type = state.get("failure_type", "unknown")
    context = state.get("retrieved_context", [])

    root_cause = (
        f"Likely {failure_type} failure. Similar context found: {len(context)} records."
        if context
        else f"Likely {failure_type} failure. No similar incidents were retrieved."
    )

    return {
        **state,
        "root_cause": root_cause,
        "recommendations": _RECOMMENDATIONS_BY_TYPE.get(
            failure_type, _RECOMMENDATIONS_BY_TYPE["unknown"]
        ),
    }


# Alias compatible con importaciones existentes (usa fallback predefinido, sin LLM).
recommend_actions = make_recommend_actions_node()
