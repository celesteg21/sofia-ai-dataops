"""
Tests de IncidentService — flujo de análisis de incidentes de punta a punta.

Estos tests verifican el comportamiento completo del flujo principal de Sofia:
desde recibir un incident_id hasta retornar un AnalysisResponse con todos
los campos esperados.

Qué se testea aquí:
    - Carga de un incidente conocido (inc_001).
    - Comportamiento cuando el incidente no existe.
    - Presencia y no-vacío de todos los campos del AnalysisResponse.
    - Coherencia del contenido (ej. el nombre del pipeline en el summary).

Qué NO se testea aquí:
    - La lógica interna de ContextService (eso está en test_context_service.py).
    - La lógica de generación del LLM (MockLLMService está implícitamente cubierta).
    - Los endpoints HTTP (los tests de integración los cubrirán en V0.3+).

Dependencias:
    - Requiere que app/mock_environment/incidents/inc_001.json exista.
    - Usa MockLLMService (LLM_BACKEND=mock por defecto) — sin modelo externo.
"""

from app.services.incident_service import IncidentService


def test_load_known_incident() -> None:
    """
    Sofia puede analizar un incidente que existe en el mock environment.

    Verifica que para inc_001 (que tiene archivo JSON, logs, metadata,
    runbook y quality results) se retorna un resultado no nulo.
    """
    service = IncidentService()
    result = service.analyze("inc_001")
    assert result is not None


def test_unknown_incident_returns_none() -> None:
    """
    Para un incident_id que no tiene archivo JSON, se retorna None.

    El router convierte este None en un 404. Este test verifica que
    el servicio no lanza excepciones ante IDs desconocidos.
    """
    service = IncidentService()
    result = service.analyze("inc_999")
    assert result is None


def test_analyze_returns_all_required_fields() -> None:
    """
    El AnalysisResponse contiene los 7 campos del diagnóstico, todos no vacíos.

    Este es el contrato más importante: cualquier cambio que haga que
    alguno de estos campos quede vacío es una regresión.
    """
    service = IncidentService()
    result = service.analyze("inc_001")
    assert result is not None
    assert result.incident_id == "inc_001"
    assert result.summary
    assert result.probable_root_cause
    assert len(result.evidence) > 0
    assert result.business_impact
    assert result.recommended_action
    assert result.long_term_improvement
    assert result.confidence in ("low", "medium", "high")


def test_analyze_includes_pipeline_in_summary() -> None:
    """
    El summary menciona el nombre del pipeline que falló.

    Verifica coherencia básica del contenido: Sofia debe identificar
    correctamente el pipeline afectado en su resumen.
    """
    service = IncidentService()
    result = service.analyze("inc_001")
    assert result is not None
    assert "daily_revenue" in result.summary
