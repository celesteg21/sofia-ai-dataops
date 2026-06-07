"""Factory de FastAPI para Sofia AI DataOps.

Objetivo: construir la aplicacion web, cargar configuracion, activar logging y registrar rutas.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from sofia_ai_dataops.api.routes import airflow, dashboard, health, incidents, memory, metrics
from sofia_ai_dataops.core.config import Settings, get_settings
from sofia_ai_dataops.core.logging import configure_logging


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings)
    app.state.settings = settings
    yield


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings)

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.settings = settings

    app.include_router(dashboard.router)
    app.include_router(health.router)
    app.include_router(airflow.router, prefix="/api/v1")
    app.include_router(incidents.router, prefix="/api/v1")
    app.include_router(memory.router, prefix="/api/v1")
    app.include_router(metrics.router, prefix="/api/v1")

    return app
