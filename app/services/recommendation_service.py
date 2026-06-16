"""
Servicio de generación de recomendaciones.

RecommendationService actúa como adaptador entre el dominio de negocio
(incidente + contexto) y el servicio LLM (que puede ser mock u Ollama).

Posición en el flujo:
    IncidentService → RecommendationService → LLMService (Mock | Ollama)

Responsabilidad:
    Única: tomar el incidente y el contexto recolectado por ContextService
    y delegar al LLMService para producir el AnalysisResponse.

Por qué existe esta capa (y no IncidentService llama al LLM directamente):
    Separa la orquestación del flujo (IncidentService) de la política de
    generación (RecommendationService). En el futuro este servicio puede:
    - Seleccionar el prompt correcto según el tipo de incidente.
    - Combinar respuestas de varios LLMs (ensemble).
    - Aplicar post-procesamiento o validación al output del LLM.
    - Gestionar reintentos con backoff si el LLM falla.

Extensión futura (V0.5 — Recommendation Engine):
    Antes de llamar al LLM, consultar el historial de incidentes similares
    y enriquecer el contexto con patrones detectados previamente.
"""

from typing import Any

from app.core.schemas import AnalysisResponse
from app.services.llm_service import LLMService, get_llm_service


class RecommendationService:
    """
    Genera el análisis final delegando en el LLMService configurado.

    El LLMService concreto se elige en el constructor vía get_llm_service(),
    que lee LLM_BACKEND desde la configuración. Cambiar de mock a Ollama
    no requiere tocar este archivo.
    """

    def __init__(self) -> None:
        # get_llm_service() lee settings.llm_backend y retorna la implementación correcta.
        # "mock"   → MockLLMService (determinístico, sin modelo).
        # "ollama" → OllamaLLMService (requiere Ollama corriendo).
        self._llm: LLMService = get_llm_service()

    def generate(self, incident: dict[str, Any], context: dict[str, Any]) -> AnalysisResponse:
        """
        Genera el diagnóstico completo para un incidente dado su contexto.

        Delega directamente en el LLMService. La lógica de construcción
        del prompt, parseo de la respuesta y mapeo a AnalysisResponse
        viven en la implementación concreta del LLM.

        Args:
            incident: Dict con los datos del incidente (pipeline, error_message,
                      severity, etc.), tal como viene del JSON del incidente.
            context:  Dict con las cuatro fuentes de contexto recolectadas por
                      ContextService: "logs", "metadata", "runbook", "quality".

        Returns:
            AnalysisResponse con los 7 campos del diagnóstico.
        """
        return self._llm.analyze(incident, context)
