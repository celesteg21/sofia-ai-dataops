"""
Tests de RunbookIndex y EmbeddingService (TF-IDF) — V0.2.

Estos tests verifican la capa de búsqueda semántica de runbooks introducida
en V0.2. Cubren tanto el servicio de embeddings directamente como la clase
RunbookIndex que lo usa, incluyendo el comportamiento del preprocesador de
texto y el umbral de similitud.

Qué se testea aquí:
    - _preprocess(): separación de camelCase, normalización de separadores.
    - TFIDFEmbeddingService: fit + similarities, edge cases (no entrenado, vacío).
    - RunbookIndex: construcción del índice sobre el mock_environment real.
    - RunbookIndex.find(): matching de errores conocidos, errores sin runbook,
      errores que no deberían matchear nada (umbral).

Qué NO se testea aquí:
    - La integración completa (ContextService.gather → RunbookReader.find):
      eso ya está cubierto en test_context_service.py.
    - La calidad subjetiva de los scores: solo verificamos que el runbook
      retornado es el correcto, no el valor numérico del score.

Dependencias:
    - Requiere que app/mock_environment/runbooks/*.json exista (3 runbooks en V0.2).
    - No requiere modelos externos ni internet.
"""

from pathlib import Path
from typing import Any

import pytest

from app.tools.embedding_service import TFIDFEmbeddingService, _preprocess
from app.tools.runbook_index import RunbookIndex, _runbook_to_text  # noqa: F401

# ---------------------------------------------------------------------------
# Tests de _preprocess
# ---------------------------------------------------------------------------


def test_preprocess_splits_camel_case() -> None:
    """
    _preprocess separa correctamente el camelCase a palabras separadas.

    "PartitionNotFoundError" es un error típico de pipelines de datos.
    Sin este split, TF-IDF lo trataría como un único token raro que
    probablemente no comparte vocabulario con el texto del runbook.
    """
    result = _preprocess("PartitionNotFoundError")
    assert "partition" in result
    assert "not" in result
    assert "found" in result
    assert "error" in result


def test_preprocess_normalizes_separators() -> None:
    """
    _preprocess convierte separadores típicos de mensajes de error en espacios.

    "raw.transactions", "dt=2026-06-04", "postgres:5432" son patrones comunes
    en logs de DataOps. Convertirlos a tokens separados mejora el matching.
    """
    result = _preprocess("raw.transactions dt=2026-06-04 postgres:5432")
    assert "." not in result
    assert "=" not in result
    assert ":" not in result


def test_preprocess_lowercases() -> None:
    """_preprocess retorna siempre minúsculas."""
    result = _preprocess("ERROR: ConnectionTimeout")
    assert result == result.lower()


# ---------------------------------------------------------------------------
# Tests de TFIDFEmbeddingService
# ---------------------------------------------------------------------------


def test_tfidf_similarities_before_fit_returns_zeros() -> None:
    """
    similarities() sin haber llamado fit() retorna lista de ceros.

    Esto protege contra el caso de un RunbookIndex con directorio vacío
    o inexistente que de todas formas llame a similarities().
    """
    svc = TFIDFEmbeddingService()
    result = svc.similarities("some error", ["runbook text"])
    assert result == [0.0]


def test_tfidf_similarities_empty_candidates() -> None:
    """similarities() con lista vacía retorna lista vacía."""
    svc = TFIDFEmbeddingService()
    svc.fit(["some text"])
    result = svc.similarities("query", [])
    assert result == []


def test_tfidf_identical_text_has_high_similarity() -> None:
    """
    Texto idéntico al corpus tiene similitud cercana a 1.0.

    Verifica el caso base: si el error es textualmente igual al contenido
    de un runbook, debe tener el score más alto.
    """
    corpus = ["partition not found error missing partition"]
    svc = TFIDFEmbeddingService()
    svc.fit(corpus)
    scores = svc.similarities("partition not found error missing partition", corpus)
    assert len(scores) == 1
    assert scores[0] > 0.9


def test_tfidf_unrelated_text_has_low_similarity() -> None:
    """
    Texto sin vocabulario compartido tiene similitud cercana a 0.

    Si el error es completamente diferente al runbook, no debe retornarlo.
    """
    corpus = ["partition not found missing data"]
    svc = TFIDFEmbeddingService()
    svc.fit(corpus)
    scores = svc.similarities("network timeout connection refused postgres", corpus)
    assert len(scores) == 1
    assert scores[0] < 0.3


def test_tfidf_returns_one_score_per_candidate() -> None:
    """similarities() retorna exactamente un score por cada candidato."""
    corpus = ["first runbook text", "second runbook text", "third runbook text"]
    svc = TFIDFEmbeddingService()
    svc.fit(corpus)
    scores = svc.similarities("some error", corpus)
    assert len(scores) == 3


# ---------------------------------------------------------------------------
# Tests de _runbook_to_text
# ---------------------------------------------------------------------------


def test_runbook_to_text_concatenates_fields() -> None:
    """_runbook_to_text incluye el contenido de los campos clave."""
    runbook: dict[str, Any] = {
        "name": "missing_partition",
        "triggers": ["PartitionNotFoundError", "partition not found"],
        "description": "Pipeline fails because partition is missing",
        "immediate_action": "Check partition and re-run",
    }
    text = _runbook_to_text(runbook)
    assert "missing_partition" in text
    assert "PartitionNotFoundError" in text
    assert "partition not found" in text
    assert "Pipeline fails" in text


def test_runbook_to_text_handles_missing_fields() -> None:
    """_runbook_to_text no lanza excepciones si faltan campos opcionales."""
    result = _runbook_to_text({})
    assert isinstance(result, str)


# ---------------------------------------------------------------------------
# Tests de RunbookIndex con el mock_environment real
# ---------------------------------------------------------------------------


RUNBOOK_DIR = Path("app/mock_environment/runbooks")


@pytest.fixture
def index() -> RunbookIndex:
    """RunbookIndex construido sobre el directorio de runbooks real."""
    return RunbookIndex(RUNBOOK_DIR)


def test_index_loads_all_runbooks(index: RunbookIndex) -> None:
    """
    RunbookIndex carga todos los runbooks del directorio.

    En V0.2 hay 3 runbooks: missing_partition, stale_data, connection_timeout.
    Este test fallará si se agrega un runbook sin actualizar el count —
    eso es intencionado: sirve de recordatorio de que el índice está creciendo.
    """
    assert index.size == 3


def test_index_finds_partition_runbook(index: RunbookIndex) -> None:
    """
    RunbookIndex encuentra el runbook de partición para un error típico.

    El error contiene "PartitionNotFoundError" — con TF-IDF + preprocesador
    camelCase esto debería coincidir con missing_partition.
    """
    result = index.find("PartitionNotFoundError: dt=2026-06-04 does not exist in raw.transactions")
    assert result
    assert result.get("name") == "missing_partition"


def test_index_finds_stale_data_runbook(index: RunbookIndex) -> None:
    """
    RunbookIndex encuentra el runbook de datos frescos para un error de SLO.

    El error menciona "freshness check failed" y "data lag" — términos
    que aparecen en los triggers de stale_data.json.
    """
    result = index.find("freshness check failed: data lag exceeds SLO window of 4 hours")
    assert result
    assert result.get("name") == "stale_data"


def test_index_finds_connection_runbook(index: RunbookIndex) -> None:
    """
    RunbookIndex encuentra el runbook de conexión para un timeout.

    El error menciona "connection timed out" — trigger directo de
    connection_timeout.json.
    """
    result = index.find("ConnectionTimeoutError: connection timed out after 30s to postgres:5432")
    assert result
    assert result.get("name") == "connection_timeout"


def test_index_returns_empty_for_unrecognized_error(index: RunbookIndex) -> None:
    """
    RunbookIndex retorna {} si el error no se parece a ningún runbook.

    Un string de gibberish no debería superar el umbral de similitud.
    """
    result = index.find("xyzzy frobnicator qux 12345 aaabbbccc")
    assert result == {}


def test_index_returns_empty_for_blank_query(index: RunbookIndex) -> None:
    """RunbookIndex retorna {} para un query en blanco."""
    assert index.find("") == {}
    assert index.find("   ") == {}


def test_index_empty_directory_returns_empty(tmp_path: Path) -> None:
    """
    RunbookIndex con directorio vacío no lanza excepciones y find() retorna {}.

    Verifica el comportamiento defensivo cuando el directorio de runbooks
    existe pero está vacío.
    """
    empty_dir = tmp_path / "runbooks"
    empty_dir.mkdir()
    idx = RunbookIndex(empty_dir)
    assert idx.size == 0
    assert idx.find("any error") == {}


def test_index_nonexistent_directory_returns_empty(tmp_path: Path) -> None:
    """
    RunbookIndex con directorio inexistente no lanza excepciones.

    El directorio puede no existir en entornos de CI que no montan el
    mock_environment completo.
    """
    idx = RunbookIndex(tmp_path / "nonexistent")
    assert idx.size == 0
    assert idx.find("any error") == {}
