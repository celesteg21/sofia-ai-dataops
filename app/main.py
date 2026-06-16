"""
Punto de entrada de la aplicación Sofia AI DataOps.

Este módulo crea la instancia de FastAPI y registra el router principal.
Es el único lugar donde se ensambla la app — no contiene lógica de negocio.

Flujo de arranque:
    1. FastAPI crea la app con título y descripción.
    2. Se registra el router de app/api/routes.py, que expone los endpoints.
    3. Al importar el router, IncidentService se instancia una vez (singleton de módulo).

Para correr localmente:
    uvicorn app.main:app --reload

Para correr en Docker:
    CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
"""

from fastapi import FastAPI

from app.api.routes import router
from app.core.config import settings

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Sofia AI DataOps — Incident Analysis Platform for Data Engineering teams.",
)
app.include_router(router)
