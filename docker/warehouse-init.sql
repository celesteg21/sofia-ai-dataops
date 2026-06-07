-- Base dummy de warehouse para el laboratorio Airflow.
-- Objetivo: tener tablas reales para simular ingestas, transformaciones y fallas de calidad.

CREATE TABLE IF NOT EXISTS raw_orders (
    order_id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL,
    amount NUMERIC(12, 2) NOT NULL,
    order_date DATE NOT NULL,
    loaded_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS staging_orders (
    order_id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL,
    amount NUMERIC(12, 2) NOT NULL,
    order_date DATE NOT NULL,
    transformed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS mart_daily_sales (
    sales_date DATE PRIMARY KEY,
    order_count INTEGER NOT NULL,
    total_amount NUMERIC(14, 2) NOT NULL,
    built_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS ingestion_audit (
    dataset_name TEXT PRIMARY KEY,
    last_successful_partition DATE,
    row_count INTEGER NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO raw_orders (order_id, customer_id, amount, order_date)
VALUES
    (1, 101, 120.50, DATE '2026-06-01'),
    (2, 102, 75.25, DATE '2026-06-01'),
    (3, 103, 42.00, DATE '2026-06-02')
ON CONFLICT (order_id) DO NOTHING;

INSERT INTO ingestion_audit (dataset_name, last_successful_partition, row_count)
VALUES ('orders', DATE '2026-06-02', 3)
ON CONFLICT (dataset_name) DO NOTHING;
