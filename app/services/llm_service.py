"""
Servicio LLM de Sofia AI DataOps.

Este módulo define la interfaz abstracta LLMService y sus dos implementaciones
actuales: MockLLMService (sin modelo, determinístico) y OllamaLLMService (stub
preparado para conectar un modelo local en V0.2).

Patrón de diseño:
    LLMService es una clase abstracta que actúa como contrato. Cualquier
    implementación (Mock, Ollama, OpenAI, Anthropic, etc.) debe implementar
    un único método: analyze(incident, context) → AnalysisResponse.
    La función de fábrica get_llm_service() decide cuál usar según la config.

Por qué es importante este aislamiento:
    - Los tests corren con MockLLMService sin necesitar modelo instalado.
    - Cambiar de mock a Ollama es una línea en .env (LLM_BACKEND=ollama).
    - Agregar un nuevo proveedor no requiere cambiar nada fuera de este archivo.
    - Los demás servicios no saben ni les importa qué LLM se usa internamente.

Flujo de datos en MockLLMService:
    incident["pipeline"]          → summary, probable_root_cause
    context["logs"]  (ERROR lines) → evidence
    context["quality"]["detail"]  → probable_root_cause, evidence, business_impact
    context["metadata"]["downstream_reports"] → business_impact
    context["runbook"]["immediate_action"]    → recommended_action
    context["runbook"]["prevention"]          → long_term_improvement

Extensión futura (V0.2):
    OllamaLLMService construirá un prompt estructurado con el incidente y el
    contexto, lo enviará a la API REST de Ollama, parseará la respuesta JSON
    y la mapeará a AnalysisResponse.
"""

from abc import ABC, abstractmethod
from typing import Any

from app.core.config import settings
from app.core.schemas import AnalysisResponse


class LLMService(ABC):
    """
    Interfaz abstracta para todos los backends LLM.

    Cualquier clase que implemente LLMService debe ser capaz de recibir
    un incidente y su contexto y producir un AnalysisResponse completo.
    Los detalles de cómo se genera (prompt, modelo, API) son internos
    a cada implementación.
    """

    @abstractmethod
    def analyze(self, incident: dict[str, Any], context: dict[str, Any]) -> AnalysisResponse:
        """
        Genera el análisis de un incidente dado su contexto.

        Args:
            incident: Dict con los datos del incidente. Claves típicas:
                      incident_id, pipeline, error_message, severity, etc.
            context:  Dict con las cuatro fuentes de contexto:
                      "logs" (str), "metadata" (dict), "runbook" (dict), "quality" (dict).

        Returns:
            AnalysisResponse con todos los campos del diagnóstico completos.
        """
        ...


class MockLLMService(LLMService):
    """
    Implementación determinística sin modelo.

    Deriva el análisis directamente de los datos estructurados del contexto
    — no usa ningún modelo de lenguaje. La respuesta es siempre la misma
    para los mismos inputs, lo que la hace ideal para tests y CI.

    Prioridades al construir cada campo:
        probable_root_cause: quality["detail"] > mensaje genérico.
        recommended_action:  runbook["immediate_action"] > fallback genérico.
        long_term_improvement: runbook["prevention"] > fallback genérico.
        evidence:            líneas ERROR/WARNING del log + quality detail.
        business_impact:     metadata["downstream_reports"] + quality["detail"].
    """

    def analyze(self, incident: dict[str, Any], context: dict[str, Any]) -> AnalysisResponse:
        """
        Construye el AnalysisResponse a partir del contexto estructurado.

        No llama a ninguna API externa. Toda la "inteligencia" viene de
        leer los campos correctos del contexto y priorizarlos.
        """
        pipeline: str = incident.get("pipeline", "unknown")
        error: str = incident.get("error_message", "unknown error")

        # Extraer cada fuente de contexto con fallback a vacío seguro.
        metadata: dict[str, Any] = context.get("metadata") or {}
        runbook: dict[str, Any] = context.get("runbook") or {}
        logs: str = context.get("logs") or ""
        quality: dict[str, Any] = context.get("quality") or {}

        # ── Impacto de negocio ────────────────────────────────────────────────
        # Si la metadata tiene la lista de reportes downstream, los incluimos.
        # Si además hay un quality check fallido, agregamos el detalle.
        downstream: list[str] = metadata.get("downstream_reports", [])
        impact = (
            f"Reports at risk: {', '.join(downstream)}."
            if downstream
            else "Downstream impact unknown."
        )
        if quality.get("detail"):
            impact += f" Quality check: {quality['detail']}"

        # ── Evidencia ────────────────────────────────────────────────────────
        # Extraemos solo las líneas con ERROR o WARNING del log — el resto
        # son INFO que no agregan valor al diagnóstico.
        evidence: list[str] = [
            line.strip() for line in logs.splitlines() if "ERROR" in line or "WARNING" in line
        ]
        if quality.get("detail"):
            # El resultado de calidad es evidencia objetiva del problema.
            evidence.append(f"Data quality: {quality['detail']}")
        if not evidence:
            # Si no hay logs ni quality, al menos incluimos el error original.
            evidence = [error]

        # ── Causa raíz ───────────────────────────────────────────────────────
        # El quality check (freshness, completeness) suele ser más preciso
        # que el mensaje de error del pipeline, que puede ser genérico.
        root_cause: str = (
            quality.get("detail")
            or f"Missing or stale upstream data required by pipeline '{pipeline}'."
        )

        # ── Acción recomendada ────────────────────────────────────────────────
        # El runbook tiene los pasos concretos para este tipo de error.
        # Si no hay runbook, damos un fallback genérico.
        action: str = (
            runbook.get("immediate_action") or "Review logs and retry the failed pipeline."
        )

        # ── Mejora estructural ────────────────────────────────────────────────
        # La sección "prevention" del runbook describe el cambio de largo plazo.
        improvement: str = (
            runbook.get("prevention")
            or "Add data quality checks before running downstream pipelines."
        )

        return AnalysisResponse(
            incident_id=incident["incident_id"],
            summary=f"Pipeline '{pipeline}' failed. Error: {error}",
            probable_root_cause=root_cause,
            evidence=evidence,
            business_impact=impact,
            recommended_action=action,
            long_term_improvement=improvement,
            confidence="medium",  # El mock siempre reporta confianza media.
        )


class OllamaLLMService(LLMService):
    """
    Stub para conectar un modelo local vía Ollama.

    Pendiente de implementación en V0.2. Cuando esté listo, construirá
    un prompt con el incidente y el contexto, llamará a la API REST de
    Ollama (settings.ollama_base_url) con el modelo configurado
    (settings.ollama_model), y mapeará la respuesta a AnalysisResponse.

    Para activar:
        LLM_BACKEND=ollama en .env
        OLLAMA_MODEL=llama3 (o cualquier modelo descargado en Ollama)
    """

    def analyze(self, incident: dict[str, Any], context: dict[str, Any]) -> AnalysisResponse:
        raise NotImplementedError(
            "OllamaLLMService is not yet implemented. Set LLM_BACKEND=mock to use the mock."
        )


def get_llm_service() -> LLMService:
    """
    Fábrica que retorna la implementación correcta de LLMService.

    Lee settings.llm_backend para decidir qué implementación instanciar.
    Es el único lugar donde se toma esa decisión — el resto del código
    trabaja contra la interfaz LLMService sin saber qué hay detrás.

    Returns:
        MockLLMService  si LLM_BACKEND="mock" (valor por defecto).
        OllamaLLMService si LLM_BACKEND="ollama".
    """
    if settings.llm_backend == "ollama":
        return OllamaLLMService()
    return MockLLMService()
