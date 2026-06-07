# Sofía — AI DataOps Agent

## Proyecto
Agente de guardia que detecta errores en Airflow, diagnostica causa raíz 
y ejecuta remediaciones automáticas.

## Stack
- Python 3.11+
- Apache Airflow (API REST v2)
- BigQuery (google-cloud-bigquery)
- PostgreSQL (metadata de Airflow)
- Pydantic v2 para modelos de datos

## Arquitectura de módulos
- `sofia/detector/` → polling de DAG runs vía Airflow API
- `sofia/context/` → carga y persistencia de contexto de errores
- `sofia/diagnosis/` → clasificación de tipo de fallo
- `sofia/remediation/` → clear, trigger y verificación de DAGs
- `sofia/memory/` → historial de incidentes y aprendizaje
- `tests/` → pytest, un test por módulo

## Reglas de código
- NUNCA hardcodear credenciales. Siempre usar variables de entorno.
- NUNCA hacer clear de un DAG sin verificar primero el estado upstream.
- Toda llamada a la Airflow API debe tener retry con backoff exponencial.
- Los errores deben clasificarse ANTES de cualquier remediación.
- Cada remediación debe tener un timeout máximo de 10 minutos.
- Logs estructurados en JSON para todos los eventos.

## Flujo de remediación (NO alterar sin consultar)
1. Detectar fallo → 2. Cargar contexto → 3. Diagnosticar causa →
4. Planificar remediación → 5. Ejecutar → 6. Verificar éxito →
7. Actualizar contexto/memoria

## Patrones establecidos
- Referencia siempre `sofia/detector/airflow_client.py` para llamadas a la API
- Referencia siempre `sofia/context/incident.py` para el modelo de incidente
- Los tests usan fixtures de `tests/conftest.py`, nunca mocks inline

## Lo que NO hacer
- No usar `requests` directamente, siempre `AirflowClient`
- No ejecutar remediaciones en paralelo sobre el mismo DAG
- No modificar el estado de Airflow sin log previo del diagnóstico
