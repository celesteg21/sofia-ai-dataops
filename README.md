<!--
  README principal del proyecto.
  Objetivo: explicar como levantar Sofia AI DataOps y orientar a nuevas personas del equipo.
-->

# Sofia AI DataOps

Plataforma para analizar incidentes de Airflow usando agentes de IA.

## Stack

- Python 3.11
- FastAPI
- LangGraph
- Qdrant
- PostgreSQL
- Docker

## Arquitectura inicial

```text
src/sofia_ai_dataops/
  api/              FastAPI app, rutas y dependencias HTTP
  agents/           Grafo LangGraph para diagnostico de incidentes
  core/             Configuracion, logging y wiring de dependencias
  db/               Clientes de PostgreSQL y Qdrant
  ingestion/        Normalizacion de logs/eventos de Airflow
  observability/    Hooks para trazas, metricas y logs estructurados
  schemas/          Contratos Pydantic de entrada/salida
  services/         Casos de uso de negocio
```

## Desarrollo local

```bash
cp .env.example .env
make setup
make run
```

La API queda disponible en `http://localhost:8000`.

La consola inicial queda disponible en `http://localhost:8000/dashboard`.

## Docker

```bash
cp .env.example .env
docker compose up --build
```

Servicios:

- API: `http://localhost:8000`
- Dashboard: `http://localhost:8000/dashboard`
- PostgreSQL: `localhost:5432`
- Qdrant: `http://localhost:6333`

Sofia indexa cada analisis en Qdrant con embeddings deterministas locales para recuperar incidentes
similares en ejecuciones posteriores. La busqueda filtra por `failure_type` cuando ya se conoce el
tipo de falla. Mas adelante esta pieza puede cambiar a embeddings de modelo.

Para reconstruir la memoria Qdrant desde los analisis guardados en PostgreSQL:

```bash
make docker-reindex-qdrant
```

## Airflow Failure Lab

Para simular DAGs fallidos y enviar incidentes reales a Sofia:

```bash
make airflow-lab-up
```

Servicios adicionales:

- Airflow: `http://localhost:8080`
- Usuario: `admin`
- Password: `admin`

Ver guia completa en `docs/airflow-lab.md`.

## Endpoints iniciales

- `GET /health`
- `POST /api/v1/airflow/task-failures`
- `GET /api/v1/incidents`
- `GET /api/v1/incidents/{analysis_id}`
- `POST /api/v1/incidents/analyze`
- `GET /api/v1/memory/status`
- `POST /api/v1/memory/reindex`

Ejemplo:

```bash
curl -X POST http://localhost:8000/api/v1/incidents/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "dag_id": "daily_sales",
    "task_id": "load_warehouse",
    "run_id": "manual__2026-06-04T00:00:00+00:00",
    "logs": "psycopg.errors.ConnectionTimeout: could not connect to server",
    "metadata": {"owner": "data-platform"}
  }'
```

## Calidad

```bash
make lint
make test
```
