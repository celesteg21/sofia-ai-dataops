"""
Endpoints HTTP de Sofia AI DataOps.

Este módulo es la capa más externa de la aplicación: recibe requests HTTP,
delega en los servicios y devuelve respuestas. No contiene lógica de negocio.

Endpoints disponibles:
    GET  /health              → verificación de vida de la API.
    POST /incidents/analyze   → análisis completo de un incidente por ID.

Diseño:
    _service se instancia una vez al importar el módulo (singleton de módulo).
    FastAPI se encarga de la validación del input (IncidentRequest) y la
    serialización del output (AnalysisResponse) via Pydantic.

Flujo de POST /incidents/analyze:
    routes.py → IncidentService.analyze()
             → ContextService.gather()      (logs, metadata, runbook, quality)
             → RecommendationService.generate()
             → LLMService.analyze()
             ← AnalysisResponse
"""

from fastapi import APIRouter, HTTPException

from app.core.schemas import AnalysisResponse, IncidentRequest
from app.services.incident_service import IncidentService

router = APIRouter()

# Instancia única del servicio principal. Se crea al importar el módulo,
# lo que inicializa también ContextService, RecommendationService y LLMService.
_service = IncidentService()


@router.get("/health")
def health() -> dict[str, str]:
    """
    Health check básico de la API.

    Retorna {"status": "ok"} si la API está corriendo. No verifica
    dependencias externas (en V0.1 no las hay). Útil para Docker
    healthchecks y monitoreo.
    """
    return {"status": "ok"}


@router.post("/incidents/analyze", response_model=AnalysisResponse)
def analyze_incident(request: IncidentRequest) -> AnalysisResponse:
    """
    Analiza un incidente y devuelve un diagnóstico estructurado.

    Recibe el ID de un incidente, busca todos los archivos de contexto
    asociados (logs, metadata, runbook, quality results) y produce un
    análisis completo con causa raíz, evidencia, impacto y recomendaciones.

    Args:
        request: Payload con el incident_id a analizar.

    Returns:
        AnalysisResponse con los 7 campos del diagnóstico.

    Raises:
        HTTPException 404: Si no existe un archivo JSON para el incident_id
                           en mock_environment/incidents/.

    Ejemplo:
        POST /incidents/analyze
        {"incident_id": "inc_001"}

        → 200 OK con el análisis completo.
        → 404 si inc_001.json no existe en mock_environment/incidents/.
    """
    result = _service.analyze(request.incident_id)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Incident '{request.incident_id}' not found in mock environment.",
        )
    return result
