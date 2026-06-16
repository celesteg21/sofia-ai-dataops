"""
Herramienta de búsqueda semántica de runbooks — V0.2.

RunbookReader expone un método find() que, dado un mensaje de error, retorna
el runbook más relevante. En V0.2 delega la búsqueda en RunbookIndex, que usa
TF-IDF para calcular similitud coseno entre el error y todos los runbooks
disponibles.

Evolución entre versiones:
    V0.1 — Keyword matching con _KEYWORD_MAP hardcodeado.
            Problema: "dt=2026-06-04 does not exist" no matcheaba
            "partition" si la palabra exacta no estaba en el error.

    V0.2 — Búsqueda semántica con TF-IDF (este archivo).
            El vectorizador aprende el vocabulario de todos los runbooks
            y calcula similitud coseno. Encuentra runbooks relevantes
            aunque el error use vocabulario diferente al del runbook.

    V0.3 — (futuro) sentence-transformers: misma interfaz, mejor calidad.
            Solo cambiaría EmbeddingService — RunbookReader no tocaría nada.

Posición en el flujo:
    ContextService → RunbookReader → RunbookIndex → EmbeddingService (TF-IDF)
                                                   → mock_environment/runbooks/*.json

Comportamiento ante runbook no encontrado:
    RunbookIndex retorna {} si ningún runbook supera el umbral de similitud.
    RunbookReader lo pasa directamente — el LLMService usa un fallback genérico.

Singleton del índice:
    RunbookIndex se instancia una sola vez en _INDEX (module-level). El índice
    es read-only después de construirse, así que es thread-safe para múltiples
    requests concurrentes sin bloqueos.
"""

from typing import Any

from app.core.config import settings
from app.tools.runbook_index import RunbookIndex

# Índice construido una vez al importar el módulo.
# Lee todos los runbooks del directorio y entrena el vectorizador TF-IDF.
# Inmutable después de construirse → thread-safe sin locks.
_INDEX = RunbookIndex(settings.mock_env_path / "runbooks")


class RunbookReader:
    """
    Encuentra el runbook más relevante para un mensaje de error.

    Wrapper fino sobre RunbookIndex. Existe como clase (en lugar de llamar
    _INDEX.find directamente) para mantener consistencia con LogReader y
    MetadataReader, y facilitar el mocking en tests futuros.
    """

    def find(self, error_message: str) -> dict[str, Any]:
        """
        Busca el runbook más relevante para el error dado.

        Delega en RunbookIndex.find(), que calcula similitud TF-IDF entre
        el error_message y todos los runbooks indexados.

        Args:
            error_message: Mensaje de error del incidente, ej.
                           "PartitionNotFoundError: dt=2026-06-04 does not exist"
                           o "ConnectionTimeoutError: could not connect to postgres:5432"

        Returns:
            Dict con el contenido del runbook más relevante (name, description,
            immediate_action, prevention), o dict vacío ({}) si ningún runbook
            supera el umbral de similitud mínimo.
        """
        return _INDEX.find(error_message)
