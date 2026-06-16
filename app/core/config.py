"""
Configuración central de Sofia AI DataOps.

Este módulo es la única fuente de verdad para variables de entorno y valores
por defecto. Todos los demás módulos importan `settings` desde aquí —
nunca leen `os.environ` directamente.

Pydantic Settings lee las variables en este orden de prioridad:
    1. Variables de entorno del sistema (mayor prioridad).
    2. Archivo .env en la raíz del proyecto.
    3. Valores por defecto definidos en la clase Settings.

Grupos de configuración:
    - App: nombre, entorno, log level, host/puerto.
    - LLM: backend a usar ("mock" o "ollama") y parámetros de Ollama.
    - Mock environment: ruta base donde viven los datos simulados.

Extensión futura:
    Para agregar un nuevo backend de LLM (OpenAI, Anthropic, etc.),
    agregar los campos aquí y crear la implementación en llm_service.py.
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Configuración typed de la aplicación.

    Todos los campos tienen valores por defecto seguros para desarrollo local.
    En producción, sobreescribir via variables de entorno o archivo .env.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # ── App ─────────────────────────────────────────────────────────────────
    app_name: str = "Sofia AI DataOps"
    app_env: str = "local"         # "local" | "staging" | "production"
    log_level: str = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # ── LLM ─────────────────────────────────────────────────────────────────
    # "mock"  → MockLLMService: determinístico, sin modelo, ideal para tests y CI.
    # "ollama" → OllamaLLMService: requiere Ollama corriendo con el modelo descargado.
    llm_backend: str = "mock"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3"

    # ── Mock environment ─────────────────────────────────────────────────────
    # Ruta base de los datos simulados. Contiene incidents/, logs/, metadata/,
    # runbooks/ y quality_results/. Relativa al directorio de trabajo.
    mock_env_path: Path = Path("app/mock_environment")


@lru_cache
def get_settings() -> Settings:
    """
    Retorna la instancia singleton de Settings.

    lru_cache garantiza que Settings() se construye una sola vez y que
    el archivo .env se lee una sola vez por proceso. En tests, se puede
    invalidar el cache con get_settings.cache_clear() si se necesita
    probar distintas configuraciones.
    """
    return Settings()


# Instancia global lista para importar directamente en cualquier módulo:
#   from app.core.config import settings
settings = get_settings()
