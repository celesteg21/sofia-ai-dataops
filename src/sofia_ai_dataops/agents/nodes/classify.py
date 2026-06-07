"""Nodo de clasificacion de incidentes.

Objetivo: inferir tipo de falla y severidad usando LLM cuando esta disponible,
con fallback a matching por keywords para garantizar que el nodo nunca bloquee.
"""

from collections.abc import Callable

import structlog
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from sofia_ai_dataops.agents.prompts import classify_v1
from sofia_ai_dataops.agents.state import IncidentGraphState
from sofia_ai_dataops.schemas.incidents import FailureType, Severity

_log = structlog.get_logger(__name__)


class _ClassificationOutput(BaseModel):
    failure_type: FailureType
    severity: Severity
    summary: str


def make_classify_incident_node(
    chat_client: ChatOpenAI | None = None,
) -> Callable[[IncidentGraphState], IncidentGraphState]:
    """Construye el nodo de clasificacion con o sin LLM."""

    def classify_incident(state: IncidentGraphState) -> IncidentGraphState:
        if chat_client is not None:
            try:
                return _classify_with_llm(chat_client, state)
            except Exception:
                _log.warning("llm_classify_fallback", exc_info=True)
        return _classify_with_keywords(state)

    return classify_incident


def _classify_with_llm(
    chat_client: ChatOpenAI,
    state: IncidentGraphState,
) -> IncidentGraphState:
    from sofia_ai_dataops.agents.llm import llm_retry

    structured_llm = chat_client.with_structured_output(_ClassificationOutput)

    @llm_retry
    def _invoke() -> _ClassificationOutput:
        return structured_llm.invoke(  # type: ignore[return-value]
            [
                SystemMessage(content=classify_v1.SYSTEM),
                HumanMessage(content=classify_v1.build_prompt(state)),
            ]
        )

    output = _invoke()
    return {
        **state,
        "failure_type": output.failure_type,
        "severity": output.severity,
        "summary": output.summary,
    }


def _classify_with_keywords(state: IncidentGraphState) -> IncidentGraphState:
    logs = state.get("logs", "").lower()
    failure_type: FailureType
    severity: Severity

    if "timeout" in logs or "could not connect" in logs:
        failure_type = "connectivity"
        severity = "high"
    elif "permission" in logs or "access denied" in logs:
        failure_type = "permissions"
        severity = "medium"
    elif "no space left" in logs or "disk" in logs:
        failure_type = "infrastructure"
        severity = "critical"
    elif (
        "upstream" in logs
        or "503" in logs
        or "service unavailable" in logs
        or "payload was empty" in logs
        or "no rows were loaded" in logs
        or "missing upstream partition" in logs
        or "has no row for partition" in logs
    ):
        failure_type = "upstream"
        severity = "high"
    else:
        failure_type = "unknown"
        severity = "medium"

    return {
        **state,
        "failure_type": failure_type,
        "severity": severity,
        "summary": f"Airflow task failed with likely {failure_type} issue.",
    }


# Alias compatible con importaciones existentes (usa fallback por keywords, sin LLM).
classify_incident = make_classify_incident_node()
