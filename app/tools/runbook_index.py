"""
Índice semántico de runbooks.

RunbookIndex carga todos los runbooks disponibles al inicializarse, construye
un índice TF-IDF sobre su contenido y expone un método find() que retorna
el runbook más relevante para un query dado (mensaje de error del incidente).

Posición en el flujo:
    RunbookReader → RunbookIndex → EmbeddingService (TF-IDF)
                                 → mock_environment/runbooks/*.json

Diferencia clave con V0.1 (keyword matching):
    V0.1: si el error no contenía exactamente "partition", no encontraba nada.
    V0.2: busca por similitud semántica sobre el texto completo del runbook.
          "dt=2026-06-04 does not exist" encuentra "missing_partition" aunque
          no mencione la palabra "partition" explícitamente.

Cómo se indexa un runbook:
    _runbook_to_text() concatena name + triggers + description + immediate_action
    en un único string. Esto le da al vectorizador todo el vocabulario relevante
    del runbook, no solo los keywords explícitos.

Umbral de similitud (threshold):
    Si el score del mejor candidato es menor que `threshold`, find() retorna
    dict vacío. Esto evita retornar un runbook irrelevante cuando el error no
    se parece a ninguno de los disponibles. El valor por defecto (0.05) es
    deliberadamente bajo para el TF-IDF con corpus pequeños — ajustar cuando
    haya más runbooks o se use un modelo semántico real.

Extensión futura:
    - top_k > 1: retornar los N runbooks más relevantes para que el LLM
      elija o combine.
    - Re-indexado en caliente: detectar cambios en el directorio y reconstruir
      el índice sin reiniciar la app.
    - Metadata filtering: filtrar runbooks por tipo de orquestador o severidad
      antes de calcular similitud.
"""

import json
from pathlib import Path
from typing import Any

from app.tools.embedding_service import EmbeddingService, get_embedding_service


def _runbook_to_text(runbook: dict[str, Any]) -> str:
    """
    Serializa un runbook a un string único para indexar.

    Concatena los campos más informativos del runbook en un texto plano.
    El orden importa: los campos más discriminativos (name, triggers)
    van primero para que reciban más peso relativo en el corpus.

    Args:
        runbook: Dict con el contenido del runbook JSON.

    Returns:
        String con el contenido relevante del runbook concatenado.
        Ejemplo: "missing partition PartitionNotFoundError missing partition
                  partition not found Pipeline fails because..."
    """
    parts = [
        runbook.get("name", ""),
        " ".join(runbook.get("triggers", [])),
        runbook.get("description", ""),
        # Solo los primeros 300 caracteres de immediate_action para no
        # sesgar demasiado el vector hacia los pasos de remediación.
        runbook.get("immediate_action", "")[:300],
    ]
    return " ".join(p for p in parts if p)


class RunbookIndex:
    """
    Índice semántico sobre todos los runbooks disponibles.

    Se construye en el __init__ cargando todos los archivos .json del
    directorio de runbooks y entrenando el vectorizador. Una vez construido,
    el índice es inmutable y thread-safe para llamadas concurrentes a find().
    """

    def __init__(self, runbook_dir: Path) -> None:
        """
        Carga todos los runbooks y construye el índice TF-IDF.

        Args:
            runbook_dir: Path al directorio que contiene los archivos .json
                         de runbooks (normalmente mock_environment/runbooks/).
                         Si el directorio no existe o está vacío, el índice
                         queda vacío y find() siempre retorna {}.
        """
        self._runbooks: list[dict[str, Any]] = []
        self._texts: list[str] = []
        self._embedding: EmbeddingService = get_embedding_service()
        self._build(runbook_dir)

    def _build(self, runbook_dir: Path) -> None:
        """
        Carga los JSONs de runbooks y entrena el vectorizador.

        Ordena los archivos por nombre para un comportamiento determinístico.
        Si el directorio no existe, termina silenciosamente (find() retornará
        siempre {}).
        """
        if not runbook_dir.exists():
            return

        for path in sorted(runbook_dir.glob("*.json")):
            runbook: dict[str, Any] = json.loads(path.read_text())
            self._runbooks.append(runbook)
            self._texts.append(_runbook_to_text(runbook))

        if self._texts:
            # Entrenamos el vectorizador con todos los textos de runbooks.
            # Esto construye el vocabulario IDF que se usará al transformar queries.
            self._embedding.fit(self._texts)

    def find(self, query: str, threshold: float = 0.05) -> dict[str, Any]:
        """
        Encuentra el runbook más relevante para el query dado.

        Calcula la similitud coseno entre el query y todos los runbooks
        indexados, retorna el de mayor score si supera el umbral.

        Args:
            query:     Texto del query, típicamente el error_message del incidente.
                       Ej: "PartitionNotFoundError: dt=2026-06-04 not in raw.transactions"
            threshold: Score mínimo de similitud para considerar un runbook relevante.
                       Valores entre 0.0 (acepta cualquier cosa) y 1.0 (coincidencia exacta).
                       Por defecto 0.05, deliberadamente bajo para TF-IDF con corpus pequeños.

        Returns:
            Dict con el contenido del runbook más relevante (name, description,
            immediate_action, prevention), o dict vacío si ningún runbook
            supera el umbral de similitud.
        """
        if not self._runbooks or not query.strip():
            return {}

        scores = self._embedding.similarities(query, self._texts)
        best_idx = int(max(range(len(scores)), key=lambda i: scores[i]))

        if scores[best_idx] < threshold:
            return {}

        return self._runbooks[best_idx]

    @property
    def size(self) -> int:
        """Número de runbooks indexados. Útil para logs y tests."""
        return len(self._runbooks)
