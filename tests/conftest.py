"""
Fixtures compartidos para los tests de Sofia AI DataOps.

En V0.1 el único fixture necesario es mock_env_path, que apunta al directorio
de datos simulados. Los servicios leen la ruta desde settings (que a su vez
la toma de .env o del valor por defecto), así que los tests funcionan
sin necesitar mocks adicionales — simplemente leen los archivos reales del
mock_environment.

Por qué los tests no necesitan mocking en V0.1:
    - No hay dependencias externas (sin DB, sin APIs, sin LLM remoto).
    - MockLLMService es determinístico — los mismos inputs siempre
      producen el mismo output.
    - Los archivos de mock_environment son parte del repo y siempre están
      disponibles en cualquier entorno (local, CI, Docker).

Extensión futura:
    Cuando se agreguen dependencias reales (Ollama en V0.2, base de datos
    en V0.5), este archivo crecerá con fixtures que provean clientes
    en memoria o stubs HTTP para que los tests sigan siendo rápidos y
    sin dependencias de infraestructura.
"""

from pathlib import Path

import pytest


@pytest.fixture
def mock_env_path() -> Path:
    """
    Retorna la ruta al directorio de datos simulados.

    Disponible para cualquier test que necesite leer archivos del
    mock environment directamente (ej. para verificar que el JSON
    de un incidente tiene la estructura esperada).

    Returns:
        Path al directorio app/mock_environment/.
    """
    return Path("app/mock_environment")
