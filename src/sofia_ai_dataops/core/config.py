"""Configuracion typed de Sofia AI DataOps.

Objetivo: leer variables de entorno y exponer settings consistentes para toda la app.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Sofia AI DataOps"
    app_env: str = "local"
    log_level: str = "INFO"

    api_host: str = "0.0.0.0"
    api_port: int = 8000

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "sofia"
    postgres_user: str = "sofia"
    postgres_password: str = "sofia"

    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "airflow_incidents"
    qdrant_vector_size: int = 64

    openai_api_key: str = Field(default="", repr=False)
    llm_model: str = "gpt-4.1-mini"
    llm_temperature: float = 0.0
    llm_max_retries: int = 3
    embedding_model: str = "text-embedding-3-small"

    @property
    def postgres_dsn(self) -> str:
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
