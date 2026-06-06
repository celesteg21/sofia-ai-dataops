# Airflow Failure Lab

Este laboratorio levanta un Airflow local con DAGs que fallan a proposito para observar como
Sofia AI DataOps analiza incidentes reales de orquestacion.

## Objetivo

Probar el comportamiento de Sofia frente a fallas tipicas de Airflow:

- timeouts contra bases de datos;
- credenciales o permisos mal configurados;
- servicios upstream caidos.

Cuando una task falla, el callback del DAG envia un payload a:

```text
POST http://api:8000/api/v1/airflow/task-failures
```

Sofia normaliza el evento de Airflow, analiza el incidente, lo clasifica y guarda el resultado.

## Servicios del laboratorio

Se levantan estos servicios:

- Sofia API: `http://localhost:8000`
- Swagger de Sofia: `http://localhost:8000/docs`
- PostgreSQL de Sofia: `localhost:5432`
- Qdrant: `http://localhost:6333`
- Airflow Webserver: `http://localhost:8080`
- PostgreSQL interno de Airflow: `localhost:5433`

Credenciales de Airflow:

```text
usuario: admin
password: admin
```

## Como levantarlo

Desde la raiz del repositorio:

```bash
cp .env.example .env
make airflow-lab-up
```

Tambien se puede correr directamente:

```bash
docker compose -f docker-compose.yml -f docker-compose.airflow.yml up --build
```

## Como usarlo

1. Abrir Airflow en `http://localhost:8080`.
2. Entrar con `admin` / `admin`.
3. Buscar los DAGs con tag `sofia` o `failure-lab`.
4. Ejecutar manualmente alguno de estos DAGs:
   - `sofia_lab_database_timeout`
   - `sofia_lab_missing_credentials`
   - `sofia_lab_upstream_failed`
5. Esperar que la task falle.
6. Abrir Swagger en `http://localhost:8000/docs`.
7. Consultar:
   - `GET /api/v1/incidents`
   - `GET /api/v1/incidents/{analysis_id}`

## DAGs incluidos

### `sofia_lab_database_timeout`

Simula un error de conexion contra una base de datos:

```text
psycopg.errors.ConnectionTimeout: could not connect to server: timeout expired
```

Sofia deberia clasificarlo como un problema de conectividad con severidad alta.

### `sofia_lab_missing_credentials`

Simula credenciales o permisos mal configurados:

```text
Permission denied: secret backend returned 403 for warehouse_user
```

Sofia deberia recomendar revisar secrets, credenciales y permisos.

### `sofia_lab_upstream_failed`

Simula una dependencia externa caida:

```text
Upstream source API returned HTTP 503 Service Unavailable
```

Sofia deberia reconocer que el origen upstream no esta disponible.

## Como apagarlo

```bash
make airflow-lab-down
```

O directamente:

```bash
docker compose -f docker-compose.yml -f docker-compose.airflow.yml down
```

## Nota

Este entorno es intencionalmente local y didactico. No representa una configuracion productiva de
Airflow. Su objetivo es permitir experimentar, generar incidentes controlados y observar el flujo
completo entre Airflow y Sofia.
