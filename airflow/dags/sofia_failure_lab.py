"""DAGs de laboratorio para Sofia AI DataOps.

Objetivo: simular fallas frecuentes de Airflow y enviar el incidente a Sofia cuando una task falla.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any

import requests
from airflow.decorators import dag, task
from airflow.exceptions import AirflowException
from airflow.models.taskinstance import TaskInstance
from requests import RequestException

SOFIA_API_URL = os.getenv("SOFIA_API_URL", "http://api:8000/api/v1/airflow/task-failures")


def send_failure_to_sofia(context: dict[str, Any]) -> None:
    task_instance = context["task_instance"]
    dag_run = context.get("dag_run")
    exception = context.get("exception")
    operator = task_instance.operator if isinstance(task_instance, TaskInstance) else None
    payload = {
        "dag_id": task_instance.dag_id,
        "task_id": task_instance.task_id,
        "run_id": dag_run.run_id if dag_run else task_instance.run_id,
        "error": str(exception) if exception else "Task failed without captured exception.",
        "try_number": task_instance.try_number,
        "log_url": task_instance.log_url,
        "execution_date": context.get("logical_date").isoformat()
        if context.get("logical_date")
        else None,
        "hostname": task_instance.hostname,
        "operator": operator,
        "metadata": {"environment": "airflow-lab"},
    }

    try:
        response = requests.post(SOFIA_API_URL, json=payload, timeout=10)
        response.raise_for_status()
    except RequestException as exc:
        task_instance.log.warning("Could not send failure event to Sofia: %s", exc)


@dag(
    dag_id="sofia_lab_database_timeout",
    description="Simula un timeout de conexion contra una base de datos.",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    tags=["sofia", "failure-lab", "database"],
)
def database_timeout_lab() -> None:
    @task(on_failure_callback=send_failure_to_sofia)
    def load_warehouse() -> None:
        raise AirflowException(
            "psycopg.errors.ConnectionTimeout: could not connect to server: timeout expired"
        )

    load_warehouse()


@dag(
    dag_id="sofia_lab_missing_credentials",
    description="Simula credenciales faltantes o mal configuradas.",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    tags=["sofia", "failure-lab", "credentials"],
)
def missing_credentials_lab() -> None:
    @task(on_failure_callback=send_failure_to_sofia)
    def read_secret() -> None:
        raise AirflowException("Permission denied: secret backend returned 403 for warehouse_user")

    read_secret()


@dag(
    dag_id="sofia_lab_upstream_failed",
    description="Simula una falla aguas arriba que bloquea una carga posterior.",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    tags=["sofia", "failure-lab", "upstream"],
)
def upstream_failure_lab() -> None:
    @task(on_failure_callback=send_failure_to_sofia)
    def extract_source() -> None:
        raise AirflowException("Upstream source API returned HTTP 503 Service Unavailable")

    @task
    def transform_payload() -> None:
        return None

    extract_source() >> transform_payload()


database_timeout_lab()
missing_credentials_lab()
upstream_failure_lab()
