"""
Servicio de embeddings para búsqueda semántica de runbooks.

Este módulo define la interfaz abstracta EmbeddingService y su primera
implementación concreta: TFIDFEmbeddingService, basada en TF-IDF de
scikit-learn. No requiere descarga de modelos ni servicios externos.

Patrón de diseño (idéntico al LLMService):
    EmbeddingService es una clase abstracta con una sola responsabilidad:
    dado un corpus de textos y un query, retornar scores de similitud.
    La función de fábrica get_embedding_service() elige la implementación
    según la configuración (hoy solo TF-IDF).

Por qué TF-IDF como primer paso:
    - Cero descargas: scikit-learn pesa ~7MB, sin modelos de lenguaje.
    - Mejor que keyword matching: encuentra similitud aunque el vocabulario
      del error y el runbook no coincidan exactamente.
    - Misma interfaz que tendrá SentenceTransformerEmbeddingService en V0.3:
      fit(corpus) + similarities(query, candidates) → scores.

Cómo reemplazar por sentence-transformers o Ollama (V0.3):
    1. Crear SentenceTransformerEmbeddingService(EmbeddingService).
    2. Implementar fit() (no-op, el modelo ya está pre-entrenado) y
       similarities() usando encode() del modelo.
    3. Cambiar get_embedding_service() para retornar la nueva clase.
    4. RunbookIndex y RunbookReader no cambian nada.

Preprocesamiento de texto:
    _preprocess() separa camelCase ("PartitionNotFoundError" →
    "partition not found error"), normaliza separadores y pasa a minúsculas.
    Esto mejora significativamente la calidad del TF-IDF para mensajes
    de error típicos de pipelines de datos.
"""

import re
from abc import ABC, abstractmethod

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity as sklearn_cosine_similarity


def _preprocess(text: str) -> str:
    """
    Normaliza texto para mejorar la calidad del TF-IDF.

    Transformaciones aplicadas:
        - Separa camelCase: "PartitionNotFoundError" → "Partition Not Found Error"
        - Reemplaza separadores (_  -  :  =  .) por espacios.
        - Convierte a minúsculas (el vectorizer también lo hace, pero aquí
          lo hacemos antes para que el split de camelCase funcione bien).

    Args:
        text: Texto original (mensaje de error, contenido de runbook, etc.)

    Returns:
        Texto normalizado listo para tokenización.

    Ejemplos:
        "PartitionNotFoundError" → "partition not found error"
        "raw.transactions"       → "raw transactions"
        "dt=2026-06-04"          → "dt 2026 06 04"
    """
    # Insertar espacio antes de mayúsculas que siguen a minúsculas (camelCase).
    text = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", text)
    # Normalizar separadores comunes en mensajes de error y paths.
    text = re.sub(r"[_\-:.=]", " ", text)
    return text.lower()


class EmbeddingService(ABC):
    """
    Interfaz abstracta para backends de embeddings.

    Define el contrato mínimo que cualquier backend debe cumplir:
    fit() para aprender el vocabulario/espacio y similarities() para
    calcular similitud entre un query y un conjunto de candidatos.

    El diseño permite swappear TF-IDF por sentence-transformers,
    Ollama embeddings u otro modelo sin tocar RunbookIndex ni RunbookReader.
    """

    @abstractmethod
    def fit(self, corpus: list[str]) -> None:
        """
        Aprende el vocabulario o espacio vectorial del corpus.

        En TF-IDF: construye el vocabulario y los pesos IDF.
        En sentence-transformers: no-op (el modelo ya está pre-entrenado).
        En Ollama: podría pre-computar y cachear los vectores del corpus.

        Args:
            corpus: Lista de textos que representan todos los runbooks.
                    Debe llamarse antes de similarities().
        """
        ...

    @abstractmethod
    def similarities(self, query: str, candidates: list[str]) -> list[float]:
        """
        Calcula la similitud coseno entre el query y cada candidato.

        Args:
            query:      Texto del query (ej. mensaje de error del incidente).
            candidates: Lista de textos de los runbooks indexados.
                        Deben ser los mismos textos usados en fit().

        Returns:
            Lista de floats en [0.0, 1.0], uno por cada candidato.
            1.0 = idénticos, 0.0 = sin relación.
        """
        ...


class TFIDFEmbeddingService(EmbeddingService):
    """
    Implementación TF-IDF de EmbeddingService usando scikit-learn.

    TF-IDF (Term Frequency — Inverse Document Frequency) pondera los
    términos según qué tan frecuentes son en el documento vs en el corpus
    completo. Términos muy comunes ("the", "a") reciben peso bajo;
    términos específicos ("PartitionNotFoundError") reciben peso alto.

    Configuración del vectorizador:
        ngram_range=(1, 2): usa tanto palabras individuales como bigramas
                            ("not found" se trata como un token adicional).
        min_df=1:           incluye términos que aparecen en al menos 1 doc
                            (importante con corpus pequeños).
        preprocessor:       aplica _preprocess() antes de tokenizar.
    """

    def __init__(self) -> None:
        self._vectorizer = TfidfVectorizer(
            lowercase=True,
            ngram_range=(1, 2),
            min_df=1,
            preprocessor=_preprocess,
        )
        self._fitted = False

    def fit(self, corpus: list[str]) -> None:
        """Construye el vocabulario TF-IDF a partir del corpus de runbooks."""
        self._vectorizer.fit(corpus)
        self._fitted = True

    def similarities(self, query: str, candidates: list[str]) -> list[float]:
        """
        Calcula similitud coseno entre el query y cada candidato.

        Transforma tanto los candidatos como el query usando el vocabulario
        aprendido en fit(), luego calcula similitud coseno.

        Retorna lista de 0.0 si el vectorizador no fue entrenado o si
        la lista de candidatos está vacía.
        """
        if not self._fitted or not candidates:
            return [0.0] * len(candidates)

        # Transformar candidatos + query en una sola llamada para eficiencia.
        matrix = self._vectorizer.transform(candidates + [query])
        query_vec = matrix[-1]
        candidate_matrix = matrix[:-1]

        scores: np.ndarray = sklearn_cosine_similarity(query_vec, candidate_matrix)[0]
        return list(scores)


def get_embedding_service() -> EmbeddingService:
    """
    Fábrica de EmbeddingService.

    Hoy retorna siempre TFIDFEmbeddingService. En V0.3+, puede leer
    settings.embedding_backend para elegir entre TF-IDF, sentence-transformers
    u Ollama, siguiendo el mismo patrón que get_llm_service().

    Returns:
        Instancia de EmbeddingService lista para usar.
    """
    return TFIDFEmbeddingService()
