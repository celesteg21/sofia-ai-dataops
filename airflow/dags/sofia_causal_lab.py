"""DAGs causales para el laboratorio Sofia AI DataOps.

Objetivo: simular una cadena DataOps real donde una falla upstream provoca fallas downstream.
"""

from __future__ import annotations

import os
from datetime import date, datetime
from typing import Any

import psycopg2
import requests
from airflow.decorators import dag, task
from airflow.exceptions import AirflowException
from airflow.models.taskinstance import TaskInstance
from requests import RequestException

SOFIA_API_URL = os.getenv("SOFIA_API_URL", "http://api:8000/api/v1/airflow/task-failures")
WAREHOUSE_DSN = os.getenv(
    "WAREHOUSE_DSN",
    "postgresql://warehouse:warehouse@warehouse-postgres:5432/warehouse",
)
LAB_PARTITION = date(2026, 6, 6)


def send_failure_to_sofia(context: dict[str, Any]) -> None:
    task_instance = context["task_instance"]
    dag_run = context.get("dag_run")
    exception = context.get("exception")
    operator = task_instance.operator if isinstance(task_instance, TaskInstance) else None
    task_metadata = dict(getattr(task_instance.task, "params", {}) or {})
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
        "metadata": {
            "environment": "airflow-causal-lab",
            "data_interval_start": str(context.get("data_interval_start")),
            "data_interval_end": str(context.get("data_interval_end")),
            **task_metadata,
        },
    }

    try:
        response = requests.post(SOFIA_API_URL, json=payload, timeout=10)
        response.raise_for_status()
    except RequestException as exc:
        task_instance.log.warning("Could not send failure event to Sofia: %s", exc)


def warehouse_query(sql: str, params: tuple[Any, ...] = ()) -> list[tuple[Any, ...]]:
    with psycopg2.connect(WAREHOUSE_DSN) as connection, connection.cursor() as cursor:
        cursor.execute(sql, params)
        if cursor.description is None:
            return []
        return list(cursor.fetchall())


def assert_partition_exists(table_name: str, partition: date) -> None:
    rows = warehouse_query(
        f"SELECT count(*) FROM {table_name} WHERE order_date = %s",
        (partition,),
    )
    count = rows[0][0]
    if count == 0:
        raise AirflowException(
            f"Missing upstream partition {partition.isoformat()} in {table_name}. "
            "The upstream ingestion DAG did not publish the expected data."
        )


@dag(
    dag_id="sofia_orders_ingest",
    description="Ingesta dummy de ordenes desde una fuente externa hacia raw_orders.",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    tags=["sofia", "causal-lab", "ingestion"],
)
def orders_ingest() -> None:
    @task(
        on_failure_callback=send_failure_to_sofia,
        params={
            "dataset": "orders",
            "table": "raw_orders",
            "partition": LAB_PARTITION.isoformat(),
            "external_dependency": "orders_api",
            "downstream_dag_ids": ["sofia_orders_transform", "sofia_sales_mart"],
            "failure_mode": "empty_source_payload",
        },
    )
    def fetch_orders_from_source() -> None:
        raise AirflowException(
            "Source API returned 200 OK but payload was empty for partition "
            f"{LAB_PARTITION.isoformat()}. No rows were loaded into raw_orders."
        )

    fetch_orders_from_source()


@dag(
    dag_id="sofia_orders_transform",
    description="Transforma raw_orders hacia staging_orders y falla si falta la particion raw.",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    tags=["sofia", "causal-lab", "transform"],
)
def orders_transform() -> None:
    @task(
        on_failure_callback=send_failure_to_sofia,
        params={
            "dataset": "orders",
            "source_table": "raw_orders",
            "target_table": "staging_orders",
            "partition": LAB_PARTITION.isoformat(),
            "upstream_dag_ids": ["sofia_orders_ingest"],
            "downstream_dag_ids": ["sofia_sales_mart", "sofia_sales_quality"],
            "failure_mode": "missing_upstream_partition",
        },
    )
    def build_staging_orders() -> None:
        assert_partition_exists("raw_orders", LAB_PARTITION)
        warehouse_query(
            """
            INSERT INTO staging_orders (order_id, customer_id, amount, order_date)
            SELECT order_id, customer_id, amount, order_date
            FROM raw_orders
            WHERE order_date = %s
            ON CONFLICT (order_id) DO UPDATE
            SET customer_id = EXCLUDED.customer_id,
                amount = EXCLUDED.amount,
                order_date = EXCLUDED.order_date,
                transformed_at = now()
            """,
            (LAB_PARTITION,),
        )

    build_staging_orders()


@dag(
    dag_id="sofia_sales_mart",
    description="Construye mart_daily_sales desde staging_orders.",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    tags=["sofia", "causal-lab", "mart"],
)
def sales_mart() -> None:
    @task(
        on_failure_callback=send_failure_to_sofia,
        params={
            "dataset": "sales",
            "source_table": "staging_orders",
            "target_table": "mart_daily_sales",
            "partition": LAB_PARTITION.isoformat(),
            "upstream_dag_ids": ["sofia_orders_transform", "sofia_orders_ingest"],
            "downstream_dag_ids": ["sofia_sales_quality"],
            "failure_mode": "missing_staging_partition",
        },
    )
    def build_daily_sales() -> None:
        assert_partition_exists("staging_orders", LAB_PARTITION)
        warehouse_query(
            """
            INSERT INTO mart_daily_sales (sales_date, order_count, total_amount)
            SELECT order_date, count(*), sum(amount)
            FROM staging_orders
            WHERE order_date = %s
            GROUP BY order_date
            ON CONFLICT (sales_date) DO UPDATE
            SET order_count = EXCLUDED.order_count,
                total_amount = EXCLUDED.total_amount,
                built_at = now()
            """,
            (LAB_PARTITION,),
        )

    build_daily_sales()


@dag(
    dag_id="sofia_sales_quality",
    description="Valida freshness y volumen del mart de ventas.",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    tags=["sofia", "causal-lab", "quality"],
)
def sales_quality() -> None:
    @task(
        on_failure_callback=send_failure_to_sofia,
        params={
            "dataset": "sales",
            "table": "mart_daily_sales",
            "partition": LAB_PARTITION.isoformat(),
            "upstream_dag_ids": ["sofia_sales_mart", "sofia_orders_transform"],
            "failure_mode": "freshness_check_failed",
        },
    )
    def validate_daily_sales() -> None:
        rows = warehouse_query(
            "SELECT order_count, total_amount FROM mart_daily_sales WHERE sales_date = %s",
            (LAB_PARTITION,),
        )
        if not rows:
            raise AirflowException(
                f"Data quality freshness check failed: mart_daily_sales has no row for "
                f"partition {LAB_PARTITION.isoformat()}. Likely caused by upstream DAG failure."
            )

        order_count, total_amount = rows[0]
        if order_count <= 0 or total_amount <= 0:
            raise AirflowException(
                "Data quality volume check failed: mart_daily_sales produced non-positive metrics."
            )

    validate_daily_sales()


orders_ingest()
orders_transform()
sales_mart()
sales_quality()
