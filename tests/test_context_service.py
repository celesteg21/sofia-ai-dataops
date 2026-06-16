"""
Tests de ContextService — recolección de contexto para un incidente.

ContextService es responsable de reunir las cuatro fuentes de contexto
que Sofia usa para generar su análisis. Estos tests verifican que cada
fuente se lee correctamente para el caso de uso principal (inc_001 /
daily_revenue) y que el comportamiento ante pipelines o errores desconocidos
es seguro (retorna vacíos, no lanza excepciones).

Qué se testea aquí:
    - Que los logs del pipeline daily_revenue se leen correctamente.
    - Que la metadata incluye dependencias y campos clave.
    - Que el RunbookReader encuentra el runbook correcto para el error de partición.
    - Que el quality result se carga y tiene el estado esperado.
    - Que para un pipeline que no existe, todas las fuentes retornan vacío.

Qué NO se testea aquí:
    - El flujo completo de análisis (eso es test_incident_service.py).
    - La generación del LLM (el LLM recibe el contexto ya formado).
"""

from typing import Any

from app.services.context_service import ContextService


def _incident(
    pipeline: str = "daily_revenue",
    error: str = "PartitionNotFoundError: Partition dt=2026-06-04 does not exist",
) -> dict[str, Any]:
    """
    Helper que construye un dict de incidente mínimo para los tests.

    Args:
        pipeline: Nombre del pipeline (determina qué archivos se buscan).
        error:    Mensaje de error (determina qué runbook se busca).

    Returns:
        Dict con las claves que ContextService necesita de un incidente.
    """
    return {"incident_id": "inc_001", "pipeline": pipeline, "error_message": error}


def test_gather_returns_non_empty_logs() -> None:
    """
    Para el pipeline daily_revenue existen logs y se leen correctamente.

    Verifica que mock_environment/logs/daily_revenue.log existe y
    que su contenido no es vacío.
    """
    ctx = ContextService().gather(_incident())
    assert ctx["logs"]


def test_gather_returns_metadata_with_dependencies() -> None:
    """
    La metadata de daily_revenue incluye el campo depends_on_pipelines.

    Verifica que mock_environment/metadata/daily_revenue.json existe,
    se parsea correctamente y contiene el campo de dependencias de pipeline.
    """
    ctx = ContextService().gather(_incident())
    assert ctx["metadata"]
    assert "depends_on_pipelines" in ctx["metadata"]


def test_gather_finds_runbook_for_partition_error() -> None:
    """
    Para un error de tipo PartitionNotFoundError se encuentra el runbook correcto.

    Verifica que RunbookReader detecta la keyword "PartitionNotFoundError"
    y carga el runbook missing_partition con el campo immediate_action.
    """
    ctx = ContextService().gather(_incident(error="PartitionNotFoundError: dt=2026-06-04"))
    assert ctx["runbook"]
    assert "immediate_action" in ctx["runbook"]


def test_gather_returns_quality_results() -> None:
    """
    Los quality results de daily_revenue se cargan y tienen estado "failed".

    Verifica que mock_environment/quality_results/daily_revenue.json existe
    y que el check de freshness refleja el problema del incidente simulado.
    """
    ctx = ContextService().gather(_incident())
    assert ctx["quality"]
    assert ctx["quality"]["status"] == "failed"


def test_gather_unknown_pipeline_returns_empty_context() -> None:
    """
    Para un pipeline que no existe, todas las fuentes retornan valores vacíos.

    Verifica el comportamiento seguro de ContextService ante datos faltantes:
    no lanza excepciones y retorna strings/dicts vacíos para cada fuente.
    El LLMService puede trabajar con contexto parcial usando sus fallbacks.
    """
    ctx = ContextService().gather(
        _incident(pipeline="nonexistent", error="xyzzy frobnicator qux 99999")
    )
    assert ctx["logs"] == ""
    assert ctx["metadata"] == {}
    assert ctx["runbook"] == {}
    assert ctx["quality"] == {}
