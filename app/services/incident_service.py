"""
Servicio principal de análisis de incidentes.

IncidentService es el punto de entrada del dominio: orquesta los pasos
necesarios para transformar un incident_id en un AnalysisResponse completo.

Posición en el flujo:
    routes.py → IncidentService → ContextService + RecommendationService

Responsabilidades:
    1. Cargar el JSON del incidente desde el mock environment.
    2. Delegar la recolección de contexto a ContextService.
    3. Delegar la generación del análisis a RecommendationService.
    4. Retornar None si el incidente no existe (el router lo convierte en 404).

Lo que NO hace:
    - No lee logs, metadata ni runbooks directamente (eso es ContextService).
    - No llama al LLM directamente (eso es RecommendationService → LLMService).
    - No expone HTTP (eso es routes.py).

Extensión futura:
    Cuando haya persistencia (V0.5), este servicio guardará el resultado
    en la base de datos y consultará historial de incidentes similares
    antes de generar el análisis.
"""

import json

from app.core.config import settings
from app.core.schemas import AnalysisResponse
from app.services.context_service import ContextService
from app.services.recommendation_service import RecommendationService


class IncidentService:
    """
    Orquestador del flujo de análisis de incidentes.

    Conecta la carga del incidente, la recolección de contexto y la
    generación de recomendaciones. Es el único punto de entrada al
    dominio desde la capa HTTP.
    """

    def __init__(self) -> None:
        # ContextService reúne toda la información disponible sobre el incidente.
        self._context = ContextService()
        # RecommendationService transforma ese contexto en un análisis estructurado.
        self._recommender = RecommendationService()

    def analyze(self, incident_id: str) -> AnalysisResponse | None:
        """
        Ejecuta el flujo completo de análisis para un incidente.

        Pasos:
            1. Busca mock_environment/incidents/{incident_id}.json.
            2. Si no existe, retorna None (el router devuelve 404).
            3. Llama a ContextService.gather() para reunir logs, metadata,
               runbook y quality results del mismo pipeline.
            4. Llama a RecommendationService.generate() que delega en el LLM.
            5. Retorna el AnalysisResponse construido por el LLM.

        Args:
            incident_id: Identificador del incidente, ej. "inc_001".
                         Debe corresponder a un archivo JSON en
                         mock_environment/incidents/.

        Returns:
            AnalysisResponse con el diagnóstico completo, o None si el
            incidente no fue encontrado.
        """
        path = settings.mock_env_path / "incidents" / f"{incident_id}.json"
        if not path.exists():
            return None

        incident = json.loads(path.read_text())
        context = self._context.gather(incident)
        return self._recommender.generate(incident, context)
