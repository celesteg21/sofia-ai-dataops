"""Dependencias reutilizables de FastAPI.

Objetivo: centralizar la construccion de servicios, repositorios y grafos para inyeccion HTTP.
"""

from functools import lru_cache

from sofia_ai_dataops.agents.incident_graph import build_incident_graph
from sofia_ai_dataops.core.config import Settings, get_settings
from sofia_ai_dataops.db.postgres import IncidentAnalysisRepository
from sofia_ai_dataops.db.qdrant import IncidentVectorStore
from sofia_ai_dataops.services.incident_service import IncidentAnalysisService
from sofia_ai_dataops.services.memory_service import IncidentMemoryService


@lru_cache
def get_incident_service() -> IncidentAnalysisService:
    settings: Settings = get_settings()
    vector_store = IncidentVectorStore(settings=settings)
    repository = IncidentAnalysisRepository(settings=settings)
    graph = build_incident_graph(vector_store=vector_store)
    return IncidentAnalysisService(graph=graph, repository=repository, vector_store=vector_store)


@lru_cache
def get_memory_service() -> IncidentMemoryService:
    settings: Settings = get_settings()
    vector_store = IncidentVectorStore(settings=settings)
    repository = IncidentAnalysisRepository(settings=settings)
    return IncidentMemoryService(repository=repository, vector_store=vector_store)
