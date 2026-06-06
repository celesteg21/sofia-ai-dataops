# Sofia AI DataOps - Contexto de la fase 1

Este documento resume el estado actual del repositorio en la primera fase del proyecto.
La idea es que sirva como memoria tecnica: que estamos construyendo, que piezas ya existen,
para que sirve cada carpeta y cual es el siguiente camino natural.

## Vision del proyecto

Sofia AI DataOps es una plataforma para analizar incidentes de Airflow usando agentes de IA.

El objetivo inicial es recibir informacion de un incidente, por ejemplo un DAG fallido, logs,
metadata y datos de ejecucion, y devolver un diagnostico estructurado con:

- severidad del incidente;
- tipo probable de falla;
- resumen del problema;
- posible causa raiz;
- recomendaciones de accion;
- contexto similar recuperado de incidentes anteriores.

En esta fase todavia no buscamos tener una plataforma productiva completa. Buscamos una base
ordenada, testeable y extensible para construir encima.

## Stack definido

- Python 3.11 como lenguaje principal.
- FastAPI para exponer la API HTTP.
- LangGraph para modelar el flujo de agentes.
- Qdrant como base vectorial para busqueda semantica de incidentes similares.
- PostgreSQL como base relacional para persistir analisis y datos durables.
- Docker y Docker Compose para levantar servicios locales.
- Ruff para linting y limpieza de codigo.
- MyPy para chequeo estricto de tipos.
- Pytest para tests automatizados.

## Que ya tenemos hoy

El repositorio ya tiene una estructura inicial de AI Engineering, separando responsabilidades por
capas:

```text
sofia-ai-dataops/
  src/sofia_ai_dataops/        Codigo fuente principal de la aplicacion
  tests/                       Tests unitarios
  docs/                        Documentacion tecnica y visual
  airflow/dags/                DAGs de laboratorio para simular fallas
  docker/                      Scripts de inicializacion de servicios
  scripts/                     Scripts auxiliares de desarrollo
  .github/workflows/           Pipeline de CI
  Dockerfile                   Imagen Docker de la API
  docker-compose.yml           Servicios locales: API, PostgreSQL y Qdrant
  docker-compose.airflow.yml   Entorno opcional con Airflow para simular incidentes
  Makefile                     Comandos frecuentes del proyecto
  pyproject.toml               Configuracion Python, dependencias y herramientas
  README.md                    Guia rapida para levantar el proyecto
  .env.example                 Variables de entorno esperadas
```

## Codigo fuente

Todo el codigo Python propio vive dentro de:

```text
src/sofia_ai_dataops/
```

Usamos la carpeta `src` porque es una buena practica en proyectos Python instalables. Ayuda a que
los tests importen el paquete real instalado y evita confusiones con archivos sueltos en la raiz.

### API

Ubicacion:

```text
src/sofia_ai_dataops/api/
```

Responsabilidad:

- crear la aplicacion FastAPI;
- registrar rutas;
- definir dependencias reutilizables;
- recibir requests HTTP;
- devolver respuestas validadas.

Endpoints iniciales:

- `GET /health`: verifica que la API este viva.
- `POST /api/v1/airflow/task-failures`: recibe fallas de tasks de Airflow y las normaliza.
- `GET /api/v1/incidents`: lista analisis recientes guardados.
- `GET /api/v1/incidents/{analysis_id}`: recupera un analisis guardado por ID.
- `POST /api/v1/incidents/analyze`: recibe un incidente normalizado y devuelve un analisis.
- `GET /api/v1/memory/status`: compara analisis en Postgres contra puntos indexados en Qdrant.
- `POST /api/v1/memory/reindex`: reconstruye memoria Qdrant desde analisis persistidos.

### Schemas

Ubicacion:

```text
src/sofia_ai_dataops/schemas/
```

Responsabilidad:

- definir contratos de entrada y salida con Pydantic;
- validar datos recibidos por la API;
- documentar la forma esperada de los objetos.

El schema principal de incidentes tiene:

- `IncidentAnalysisRequest`: payload de entrada.
- `IncidentAnalysisResponse`: respuesta del analisis.
- `FailureType`: tipos de falla permitidos.
- `Severity`: severidades permitidas: `low`, `medium`, `high`, `critical`.

Tambien existe `AirflowTaskFailureEvent`, que representa el contrato especifico de fallas de tasks
provenientes de Airflow.

### Services

Ubicacion:

```text
src/sofia_ai_dataops/services/
```

Responsabilidad:

- contener casos de uso de negocio;
- coordinar el grafo de agentes;
- persistir resultados;
- mantener la API separada de la logica interna.

El servicio principal es `IncidentAnalysisService`, que recibe un incidente, ejecuta el grafo,
construye la respuesta, guarda el resultado y emite un evento de observabilidad.

Tambien expone consultas de lectura para recuperar analisis guardados por ID o listar los mas
recientes.

### Agents

Ubicacion:

```text
src/sofia_ai_dataops/agents/
```

Responsabilidad:

- definir el estado compartido del agente;
- construir el workflow LangGraph;
- separar cada paso del razonamiento en nodos.

Grafo actual:

```text
classify_incident -> retrieve_context -> recommend_actions -> END
```

Nodos actuales:

- `classify_incident`: clasifica severidad y tipo probable del incidente.
- `retrieve_context`: busca contexto similar en Qdrant filtrando por tipo de falla cuando aplica.
- `recommend_actions`: genera resumen, causa raiz y recomendaciones.

En esta fase, el flujo esta preparado para crecer. Mas adelante podemos agregar nodos para
normalizar logs, llamar modelos LLM, pedir aprobacion humana, generar tickets o consultar
documentacion interna.

### DB

Ubicacion:

```text
src/sofia_ai_dataops/db/
```

Responsabilidad:

- concentrar integraciones con bases de datos;
- aislar detalles de PostgreSQL y Qdrant;
- permitir que servicios y agentes no dependan directamente de clientes externos.

Componentes actuales:

- `postgres.py`: repositorio para guardar, recuperar y listar analisis.
- `qdrant.py`: memoria vectorial para indexar analisis y recuperar incidentes similares.

Qdrant ya puede crear la coleccion automaticamente, generar embeddings deterministas locales,
guardar analisis y recuperar contexto similar. La recuperacion usa el `failure_type` inferido para
filtrar resultados y evitar mezclar incidentes de categorias distintas cuando el tipo de falla es
conocido. Esta implementacion permite probar memoria end-to-end sin depender todavia de una API
externa de embeddings.

Tambien existe un reindexado operativo para reconstruir la memoria desde PostgreSQL:

```bash
make docker-reindex-qdrant
```

La misma operacion se puede inspeccionar y ejecutar desde la API:

```text
GET /api/v1/memory/status
POST /api/v1/memory/reindex
```

### Ingestion

Ubicacion:

```text
src/sofia_ai_dataops/ingestion/
```

Responsabilidad:

- recibir o transformar datos provenientes de Airflow;
- normalizar logs, DAG IDs, task IDs, run IDs y metadata;
- preparar datos antes de mandarlos al grafo.

En fase 2 ya convierte eventos `AirflowTaskFailureEvent` en `IncidentAnalysisRequest`, agregando
`source="airflow"` y metadata operativa como intentos, URL de logs, operador y fecha de ejecucion.

### Observability

Ubicacion:

```text
src/sofia_ai_dataops/observability/
```

Responsabilidad:

- registrar eventos importantes;
- preparar el proyecto para logs estructurados, metricas y trazas;
- facilitar diagnostico del propio sistema.

Evento actual:

- `log_incident_analyzed`: registra que un incidente fue analizado.

### Core

Ubicacion:

```text
src/sofia_ai_dataops/core/
```

Responsabilidad:

- configuracion central;
- variables de entorno;
- logging base;
- piezas compartidas por toda la app.

## Infraestructura local

### Dockerfile

Define como construir la imagen de la API.

Sirve para correr la aplicacion de forma reproducible sin depender tanto de la maquina local.

### docker-compose.yml

Levanta los servicios principales:

- API FastAPI en `http://localhost:8000`;
- PostgreSQL en `localhost:5432`;
- Qdrant en `http://localhost:6333`.

### docker-compose.airflow.yml

Levanta un laboratorio opcional con Airflow para simular DAGs fallidos.

Servicios adicionales:

- Airflow Webserver en `http://localhost:8080`;
- PostgreSQL interno de Airflow en `localhost:5433`;
- DAGs de prueba montados desde `airflow/dags`.

Este compose se usa junto con el compose base, para que Airflow pueda llamar a la API de Sofia.

### docker/postgres-init.sql

Script inicial para preparar PostgreSQL cuando el contenedor arranca por primera vez.

## Airflow Failure Lab

Ubicacion:

```text
airflow/dags/
docs/airflow-lab.md
```

Responsabilidad:

- levantar un Airflow local;
- mostrar DAGs reales en la UI de Airflow;
- simular fallas controladas;
- enviar errores a Sofia usando callbacks de Airflow;
- observar el resultado desde la API de Sofia.

DAGs actuales:

- `sofia_lab_database_timeout`: simula timeout de base de datos.
- `sofia_lab_missing_credentials`: simula credenciales o permisos invalidos.
- `sofia_lab_upstream_failed`: simula una dependencia externa caida.

Comando principal:

```bash
make airflow-lab-up
```

## Calidad y desarrollo

### pyproject.toml

Es el archivo central de configuracion Python. Define:

- nombre y version del paquete;
- dependencias runtime;
- dependencias de desarrollo;
- configuracion de Pytest;
- reglas de Ruff;
- configuracion estricta de MyPy;
- layout del paquete con `src`.

### Makefile

Agrupa comandos frecuentes:

- instalar dependencias;
- correr tests;
- correr lint;
- levantar la API;
- levantar servicios Docker.
- reindexar la memoria Qdrant desde PostgreSQL.

### scripts/dev_check.sh

Script de chequeo local. Ejecuta:

```bash
ruff check .
mypy src
pytest
```

Es util antes de commitear o abrir un pull request.

### Tests

Ubicacion:

```text
tests/unit/
```

Tests actuales:

- `test_airflow_ingestion.py`: valida normalizacion Airflow -> Sofia y endpoint de ingesta.
- `test_health.py`: valida el endpoint de health.
- `test_incident_nodes.py`: valida nodos iniciales del grafo de incidentes.
- `test_incident_repository.py`: valida persistencia de analisis con una base en memoria.
- `test_memory_service.py`: valida reindexado de memoria desde analisis persistidos.
- `test_memory_routes.py`: valida endpoints operativos de memoria.
- `test_qdrant_vector_store.py`: valida indexado y busqueda de contexto similar en Qdrant.

## Archivos generados que no forman parte del codigo fuente

Durante el desarrollo pueden aparecer carpetas como:

- `.venv/`: entorno virtual local de Python.
- `.pytest_cache/`: cache generado por Pytest.
- `.ruff_cache/`: cache generado por Ruff.
- `.mypy_cache/`: cache generado por MyPy.
- `src/sofia_ai_dataops.egg-info/`: metadata generada al instalar el paquete en modo editable.

Estas carpetas no son la logica del proyecto. Son archivos generados por herramientas y no deberian
editarse a mano ni commitearse.

## Comandos utiles

Crear entorno local:

```bash
cp .env.example .env
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Correr API local:

```bash
make run
```

Correr chequeos:

```bash
make lint
make test
scripts/dev_check.sh
```

Levantar servicios con Docker:

```bash
docker compose up --build
```

Levantar laboratorio Airflow:

```bash
make airflow-lab-up
```

## Estado actual de la fase 1

Ya esta creada la base del proyecto:

- estructura modular del backend;
- API FastAPI inicial;
- endpoint de health;
- endpoint dedicado de ingesta Airflow;
- endpoint inicial de analisis de incidentes;
- endpoints para consultar analisis persistidos;
- dashboard inicial en `/dashboard` para explorar incidentes y memoria;
- grafo LangGraph basico;
- schemas Pydantic para incidentes y eventos Airflow;
- persistencia en PostgreSQL para guardar y leer analisis enriquecidos;
- almacenamiento de `failure_type`, `metadata`, `retrieved_context`, `source` y `created_at`;
- memoria en Qdrant para indexar, reindexar y recuperar incidentes similares filtrados por tipo de falla;
- laboratorio Airflow con DAGs que fallan y reportan incidentes a Sofia;
- Docker Compose;
- tests unitarios;
- CI inicial;
- documentacion de arquitectura;
- HTML explicando la estructura del repositorio;
- comentarios/docstrings en archivos principales para facilitar aprendizaje.

## Que falta para siguientes fases

Posibles proximos pasos:

- conectar un LLM real para clasificacion y recomendaciones;
- definir prompts versionados;
- reemplazar embeddings deterministas por embeddings semanticos de modelo;
- ingerir historiales de Airflow;
- agregar autenticacion;
- agregar observabilidad mas completa;
- crear evaluaciones offline para medir calidad de respuestas;
- agregar redaccion de PII en logs;
- agregar reintentos y politicas de fallback de modelo;
- crear UI o dashboard para consultar incidentes;
- integrar GitHub Issues, Slack, Jira u otro sistema de alertas;
- preparar despliegue productivo.

## Principio de diseno de esta fase

La prioridad de esta primera fase es tener una base clara antes de agregar inteligencia compleja.

El proyecto esta organizado para que cada parte tenga una responsabilidad concreta:

- la API habla HTTP;
- los services coordinan casos de uso;
- los agents razonan;
- `db` guarda o recupera datos;
- `schemas` valida contratos;
- `core` configura;
- `observability` permite entender que paso.

Esa separacion hace que Sofia AI DataOps pueda crecer sin convertirse rapidamente en un archivo
gigante dificil de mantener.
