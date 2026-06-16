"""
Herramienta de lectura de logs de pipeline.

LogReader es una herramienta (tool) de bajo nivel: sabe cómo leer un archivo
de log del mock environment, pero no interpreta su contenido. La interpretación
(qué líneas son relevantes, qué significan) ocurre en el LLMService.

Posición en el flujo:
    ContextService → LogReader → mock_environment/logs/{pipeline}.log

Convención de nombres de archivo:
    El log de un pipeline "daily_revenue" se espera en:
    mock_environment/logs/daily_revenue.log

    Cuando los OrchestratorAdapters reales estén disponibles (V0.4),
    este reader puede complementarse o reemplazarse por uno que llame
    a la API de Airflow/Dagster para obtener logs en vivo.

Comportamiento ante archivo faltante:
    Retorna string vacío ("") — el ContextService y el LLMService
    pueden trabajar con contexto parcial sin lanzar excepciones.
"""

from app.core.config import settings


class LogReader:
    """
    Lee el archivo de log de un pipeline desde el mock environment.

    Herramienta stateless: no guarda estado entre llamadas. Cada llamada
    a read() abre y lee el archivo desde disco.
    """

    def read(self, pipeline: str) -> str:
        """
        Lee el log completo de un pipeline.

        Args:
            pipeline: Nombre del pipeline, ej. "daily_revenue".
                      Se usa para construir el path:
                      {mock_env_path}/logs/{pipeline}.log

        Returns:
            Contenido completo del archivo .log como string.
            String vacío ("") si el archivo no existe.
        """
        path = settings.mock_env_path / "logs" / f"{pipeline}.log"
        if not path.exists():
            return ""
        return path.read_text()
