"""
Interfaz base para adapters de orquestadores de pipelines.

Este módulo define el contrato que cualquier integración con un orquestador
real debe cumplir. En V0.1 solo existe MockOrchestratorAdapter, que retorna
datos estáticos sin conectarse a ningún sistema.

Por qué existe esta capa (en lugar de llamar a Airflow directamente):
    - El resto de la app nunca depende de Airflow, Dagster o Prefect.
    - Cambiar de orquestador es implementar esta interfaz — sin tocar servicios.
    - Los tests pueden correr con el mock sin necesitar un orquestador real.
    - Permite soportar múltiples orquestadores simultáneamente si el equipo
      usa más de uno (ej. Airflow para ETL y Prefect para ML pipelines).

Implementaciones planificadas (V0.4 — Orchestrator Adapters):
    AirflowAdapter:       llama a la Airflow REST API v2.
    DagsterAdapter:       consulta las GraphQL APIs de Dagster.
    PrefectAdapter:       usa el cliente de Prefect Cloud/Server.
    StepFunctionsAdapter: consulta AWS Step Functions via boto3.

Cómo agregar un nuevo adapter:
    1. Crear app/tools/{nombre}_adapter.py.
    2. Definir una clase que extienda OrchestratorAdapter.
    3. Implementar get_run_status, trigger_run y get_logs.
    4. Wirear en ContextService o en un nuevo servicio de contexto live.
"""

from abc import ABC, abstractmethod
from typing import Any


class OrchestratorAdapter(ABC):
    """
    Contrato base para integraciones con orquestadores de pipelines.

    Define las tres operaciones fundamentales que Sofia necesita de
    cualquier orquestador: consultar estado, disparar una ejecución
    y obtener logs.

    Todas las implementaciones concretas deben ser stateless o manejar
    su estado interno (autenticación, sesión HTTP) sin exponer detalles
    al resto de la app.
    """

    @abstractmethod
    def get_run_status(self, pipeline_id: str, run_id: str) -> dict[str, Any]:
        """
        Retorna el estado actual de una ejecución de pipeline.

        Args:
            pipeline_id: Identificador del pipeline (DAG ID, job name, etc.).
            run_id:      Identificador de la ejecución específica.

        Returns:
            Dict con al menos "status" ("running" | "failed" | "success" | "skipped")
            y cualquier información adicional del orquestador.
        """
        ...

    @abstractmethod
    def trigger_run(self, pipeline_id: str, params: dict[str, Any]) -> str:
        """
        Dispara una nueva ejecución del pipeline.

        Usado en el flujo de remediación: Sofia puede reejecutar una
        ingesta que falló antes de reintentar el pipeline dependiente.

        Args:
            pipeline_id: Identificador del pipeline a ejecutar.
            params:      Parámetros de la ejecución (ej. {"date": "2026-06-04"}).

        Returns:
            ID de la nueva ejecución disparada.
        """
        ...

    @abstractmethod
    def get_logs(self, pipeline_id: str, run_id: str) -> str:
        """
        Obtiene los logs de una ejecución de pipeline.

        En V0.1 los logs se leen de archivos locales (LogReader).
        En V0.4 este método los obtendrá directamente del orquestador,
        lo que permitirá trabajar con logs en tiempo real.

        Args:
            pipeline_id: Identificador del pipeline.
            run_id:      Identificador de la ejecución.

        Returns:
            Log completo de la ejecución como string.
        """
        ...


class MockOrchestratorAdapter(OrchestratorAdapter):
    """
    Adapter mock para desarrollo local y tests.

    Retorna respuestas estáticas sin conectarse a ningún orquestador.
    Útil para probar el flujo de remediación (V0.6) antes de tener
    los adapters reales implementados.
    """

    def get_run_status(self, pipeline_id: str, run_id: str) -> dict[str, Any]:
        """Simula un pipeline en estado fallido."""
        return {"status": "failed", "pipeline_id": pipeline_id, "run_id": run_id}

    def trigger_run(self, pipeline_id: str, params: dict[str, Any]) -> str:
        """Simula el disparo de una ejecución retornando un run_id ficticio."""
        return f"mock_run_{pipeline_id}"

    def get_logs(self, pipeline_id: str, run_id: str) -> str:
        """Retorna un placeholder indicando que no hay logs reales disponibles."""
        return f"[MOCK] No logs available for {pipeline_id}/{run_id}"
