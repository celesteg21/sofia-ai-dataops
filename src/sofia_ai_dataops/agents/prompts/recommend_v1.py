"""Prompt v1 para recomendaciones de remediacion de incidentes."""

from sofia_ai_dataops.agents.state import IncidentGraphState

SYSTEM = """\
Eres un Site Reliability Engineer experto en Apache Airflow y pipelines de datos.
Dado el contexto de un incidente, debes:
1. Identificar la causa raíz más probable (2-3 oraciones concretas).
2. Proporcionar entre 2 y 5 pasos de remediación accionables y específicos.

Sé directo y específico. Evita respuestas genéricas. Usa la información del tipo de falla
y el contexto de incidentes similares para personalizar el análisis.\
"""


def build_prompt(state: IncidentGraphState) -> str:
    logs_excerpt = (state.get("logs") or "Sin logs disponibles")[:1500]
    context_items = state.get("retrieved_context") or []
    context_text = (
        "\n".join(f"- {c}" for c in context_items) or "Sin incidentes similares encontrados."
    )

    return f"""\
Incidente:
- DAG: {state.get("dag_id", "desconocido")} / Task: {state.get("task_id", "desconocido")}
- Tipo de falla: {state.get("failure_type", "unknown")}
- Severidad: {state.get("severity", "medium")}
- Resumen: {state.get("summary", "Sin resumen")}

Extracto de logs:
{logs_excerpt}

Incidentes similares previos:
{context_text}

Proporciona la causa raíz y los pasos de remediación.\
"""
