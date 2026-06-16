"""
Servicio de recolección de contexto para un incidente.

ContextService es responsable de reunir toda la información disponible
sobre un incidente antes de pasársela al LLM. Es el agregador de contexto:
sabe qué herramientas existen y cómo coordinarlas, pero no interpreta
los datos — eso le corresponde al LLMService.

Posición en el flujo:
    IncidentService → ContextService → LogReader
                                    → MetadataReader
                                    → RunbookReader
                                    → (quality results, inline)

Fuentes de contexto actuales (V0.1):
    logs:     Salida de ejecución del pipeline (errores, warnings, timestamps).
    metadata: Definición del pipeline (dependencias, downstream, schedule, SLA).
    runbook:  Playbook de remediación para el tipo de error detectado.
    quality:  Resultado del último check de calidad del pipeline (freshness, etc.).

Extensión futura (V0.3 — Metadata & Lineage):
    Agregar graph_reader para consultar el grafo de linaje y determinar
    automáticamente todos los sistemas upstream/downstream afectados.

Extensión futura (V0.4 — Orchestrator Adapters):
    Agregar una fuente de contexto que llame al OrchestratorAdapter
    real (Airflow, Dagster) para obtener logs y estado en vivo.
"""

import json
from typing import Any

from app.core.config import settings
from app.tools.log_reader import LogReader
from app.tools.metadata_reader import MetadataReader
from app.tools.runbook_reader import RunbookReader


class ContextService:
    """
    Agrega contexto de múltiples fuentes para un incidente dado.

    Instancia las herramientas de lectura una sola vez en el constructor
    y las reutiliza en cada llamada a gather(). Esto permite que en el
    futuro las herramientas tengan estado (caché, conexión HTTP abierta, etc.)
    sin cambiar la interfaz de ContextService.
    """

    def __init__(self) -> None:
        self._logs = LogReader()          # Lee archivos .log del pipeline.
        self._metadata = MetadataReader() # Lee el JSON de definición del pipeline.
        self._runbooks = RunbookReader()  # Busca el runbook relevante por keywords.

    def gather(self, incident: dict[str, Any]) -> dict[str, Any]:
        """
        Reúne todo el contexto disponible para un incidente.

        Lee en paralelo (en la práctica secuencialmente en V0.1) cada fuente
        de contexto y las empaqueta en un dict que el LLMService puede consumir.
        Si alguna fuente no tiene datos para el pipeline (archivo no existe),
        devuelve un valor vacío sin lanzar excepciones — el LLM puede trabajar
        con contexto parcial.

        Args:
            incident: Dict con los datos del incidente. Claves relevantes:
                      - "pipeline": nombre del pipeline (ej. "daily_revenue").
                        Se usa para buscar logs, metadata y quality results.
                      - "error_message": mensaje de error del incidente.
                        Se usa para buscar el runbook más relevante.

        Returns:
            Dict con cuatro claves:
                "logs"     (str):            Contenido completo del archivo .log.
                                             Vacío ("") si no existe el archivo.
                "metadata" (dict[str, Any]): Definición del pipeline.
                                             Vacío ({}) si no existe el archivo.
                "runbook"  (dict[str, Any]): Playbook de remediación encontrado.
                                             Vacío ({}) si ningún keyword coincide.
                "quality"  (dict[str, Any]): Último resultado de calidad.
                                             Vacío ({}) si no existe el archivo.
        """
        pipeline: str = incident.get("pipeline", "")
        error: str = incident.get("error_message", "")

        # Quality results se leen inline porque aún no tienen su propia herramienta.
        # En V0.2+ se puede extraer a un QualityReader siguiendo el mismo patrón
        # que LogReader y MetadataReader.
        quality_path = settings.mock_env_path / "quality_results" / f"{pipeline}.json"
        quality: dict[str, Any] = (
            json.loads(quality_path.read_text()) if quality_path.exists() else {}
        )

        return {
            "logs": self._logs.read(pipeline),
            "metadata": self._metadata.read(pipeline),
            "runbook": self._runbooks.find(error),
            "quality": quality,
        }
