"""Reconstruye la memoria Qdrant desde PostgreSQL.

Objetivo: recuperar la memoria vectorial cuando la coleccion se borra o cambia la estrategia.
"""

import argparse

from sofia_ai_dataops.core.config import get_settings
from sofia_ai_dataops.db.postgres import IncidentAnalysisRepository
from sofia_ai_dataops.db.qdrant import IncidentVectorStore
from sofia_ai_dataops.services.memory_service import IncidentMemoryService


def main() -> None:
    parser = argparse.ArgumentParser(description="Reindex incident analyses into Qdrant.")
    parser.add_argument("--limit", type=int, default=1000)
    args = parser.parse_args()

    settings = get_settings()
    repository = IncidentAnalysisRepository(settings=settings)
    vector_store = IncidentVectorStore(settings=settings)
    service = IncidentMemoryService(repository=repository, vector_store=vector_store)

    result = service.reindex_recent(limit=args.limit)
    print(
        f"Indexed {result.indexed}/{result.total_available} incident analyses "
        f"into Qdrant collection '{settings.qdrant_collection}'."
    )


if __name__ == "__main__":
    main()
