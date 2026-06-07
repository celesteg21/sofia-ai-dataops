"""Prompt v1 para clasificacion de incidentes de Airflow."""

from sofia_ai_dataops.agents.state import IncidentGraphState

SYSTEM = """\
Eres un experto en diagnóstico de incidentes de Apache Airflow.
Tu tarea es clasificar el incidente descrito en uno de los siguientes tipos de falla:

- connectivity: timeouts de red, fallas de conexión a bases de datos o servicios, problemas DNS
- permissions: acceso denegado, credenciales inválidas, errores de autenticación o autorización
- infrastructure: disco lleno, memoria agotada, crash de worker, problemas de scheduler
- upstream: dependencia fallida, payload vacío, partición upstream faltante, servicio externo caído
- unknown: cualquier otra falla que no encaje claramente en las categorías anteriores

Y también la severidad:
- low: problema menor, pipeline no crítico, fácil de recuperar
- medium: funcionalidad degradada, impacto en negocio poco claro
- high: impacto significativo en negocio, requiere atención pronta
- critical: outage completo, riesgo de pérdida de datos, acción inmediata requerida

Responde SOLO con el JSON estructurado solicitado. No agregues explicaciones extra.\
"""


def build_prompt(state: IncidentGraphState) -> str:
    logs_excerpt = (state.get("logs") or "Sin logs disponibles")[:2000]
    return f"""\
Detalles del incidente:
- DAG: {state.get("dag_id", "desconocido")}
- Task: {state.get("task_id", "desconocido")}
- Run: {state.get("run_id", "desconocido")}

Extracto de logs:
{logs_excerpt}

Clasifica este incidente indicando failure_type, severity y un summary de una línea.\
"""
