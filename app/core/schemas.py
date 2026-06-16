"""
Contratos de entrada y salida de la API de Sofia AI DataOps.

Este módulo define los modelos Pydantic que se usan en los endpoints HTTP.
Su única responsabilidad es describir la forma de los datos — no contiene
lógica de negocio.

Modelos:
    IncidentRequest  → lo que recibe el endpoint POST /incidents/analyze.
    AnalysisResponse → lo que devuelve el mismo endpoint.

Convención de diseño:
    Si el contrato de la API necesita cambiar (nuevos campos, tipos distintos),
    este es el único archivo que hay que tocar. Los servicios internos pueden
    usar dicts tipados con Any mientras trabajan; solo al momento de retornar
    construyen un AnalysisResponse.
"""

from typing import Literal

from pydantic import BaseModel


class IncidentRequest(BaseModel):
    """
    Payload de entrada para el análisis de un incidente.

    El cliente solo necesita saber el ID del incidente. Sofia busca
    internamente todos los archivos de contexto asociados a ese ID
    (logs, metadata, runbooks, quality results).

    Ejemplo de uso:
        POST /incidents/analyze
        {"incident_id": "inc_001"}
    """

    incident_id: str


class AnalysisResponse(BaseModel):
    """
    Respuesta estructurada del análisis de un incidente.

    Cada campo representa una dimensión distinta del diagnóstico que
    Sofia produce. El objetivo es que un Data Engineer pueda actuar
    leyendo solo esta respuesta, sin necesitar investigar manualmente.

    Campos:
        incident_id:           ID del incidente analizado (espejo del input).
        summary:               Descripción corta de qué falló y cuál fue el error exacto.
        probable_root_cause:   Causa raíz inferida del contexto (logs, quality checks).
                               Puede diferir del mensaje de error superficial.
        evidence:              Lista de líneas de log o resultados de calidad que
                               sustentan el diagnóstico. Sofia siempre muestra su trabajo.
        business_impact:       Qué reportes, datasets o procesos downstream están
                               afectados en este momento.
        recommended_action:    Pasos concretos y ordenados para resolver el incidente
                               ahora, generalmente derivados del runbook relevante.
        long_term_improvement: Cambio estructural para evitar que este incidente
                               vuelva a ocurrir (sensor de freshness, gate de calidad, etc.).
        confidence:            Nivel de confianza del análisis. "medium" es el valor
                               por defecto del MockLLMService. Un LLM real puede
                               calibrar esto según la evidencia disponible.
    """

    incident_id: str
    summary: str
    probable_root_cause: str
    evidence: list[str]
    business_impact: str
    recommended_action: str
    long_term_improvement: str
    confidence: Literal["low", "medium", "high"]
