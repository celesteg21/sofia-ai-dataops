"""
Herramienta de lectura de metadata de pipeline.

MetadataReader lee el JSON de definición de un pipeline desde el mock
environment. La metadata describe la estructura del pipeline: de qué
tablas depende, qué reportes alimenta, cuál es su schedule y su SLA.

Esta información es crítica para que el LLM pueda determinar el impacto
de negocio de un incidente — sin metadata, Sofia no sabe qué reportes
están en riesgo cuando un pipeline falla.

Posición en el flujo:
    ContextService → MetadataReader → mock_environment/metadata/{pipeline}.json

Convención de nombres de archivo:
    La metadata de "daily_revenue" se espera en:
    mock_environment/metadata/daily_revenue.json

Campos típicos del JSON de metadata:
    pipeline:              nombre del pipeline.
    depends_on_tables:     tablas upstream que necesita.
    depends_on_pipelines:  pipelines upstream que deben correr antes.
    output_tables:         tablas que produce.
    downstream_reports:    reportes de negocio que consumen su output.
    schedule:              cron expression de cuándo corre.
    expected_freshness_hours: cuántas horas puede tolerar de lag.
    sla_minutes:           SLA de entrega del resultado.

Comportamiento ante archivo faltante:
    Retorna dict vacío ({}) — el LLM puede trabajar con metadata parcial.
"""

import json
from typing import Any

from app.core.config import settings


class MetadataReader:
    """
    Lee el JSON de definición y dependencias de un pipeline.

    Herramienta stateless. Cada llamada a read() lee el archivo desde disco.
    """

    def read(self, pipeline: str) -> dict[str, Any]:
        """
        Lee la metadata completa de un pipeline.

        Args:
            pipeline: Nombre del pipeline, ej. "daily_revenue".
                      Se usa para construir el path:
                      {mock_env_path}/metadata/{pipeline}.json

        Returns:
            Dict con todos los campos de metadata del pipeline.
            Dict vacío ({}) si el archivo no existe.
        """
        path = settings.mock_env_path / "metadata" / f"{pipeline}.json"
        if not path.exists():
            return {}
        data: dict[str, Any] = json.loads(path.read_text())
        return data
