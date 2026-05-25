"""DAG: Export Gold tables from DuckDB → PostgreSQL.

Triggered by run_dbt_transform DAG completion.
"""
from __future__ import annotations

from datetime import datetime

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.common.sql.operators.sql import SQLExecuteQueryOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator

from idp.core.config import settings
from idp.orchestration.dag_utils import default_dag_args
from idp.transform.export import PostgresExportService

DAG_ID = "export_gold_to_postgres"


def _export_gold(**ctx):
    PostgresExportService(
        duckdb_path=str(settings.duckdb_path)
    ).export_tables()


with DAG(
    dag_id=DAG_ID,
    default_args=default_dag_args(retries=2, retry_delay_minutes=2),
    description="Export Gold tables from DuckDB to PostgreSQL",
    schedule=None,
    start_date=datetime(2024, 1, 1),
    max_active_runs=1,
    catchup=False,
    tags=["export", "gold"],
) as dag:

    export = PythonOperator(
        task_id="export_gold_tables",
        python_callable=_export_gold,
    )

    for table_name in ["dim_countries", "dim_indicators", "dim_dates", "fact_economic_indicators"]:
        verify = SQLExecuteQueryOperator(
            task_id=f"verify_{table_name}",
            sql=f"SELECT count(*) FROM gold.{table_name};",
            conn_id="postgres_warehouse",
        )
        export >> verify

    trigger_embeddings = TriggerDagRunOperator(
        task_id='trigger_embeddings',
        trigger_dag_id='refresh_embeddings',
        wait_for_completion=False
    )

    trigger_graph = TriggerDagRunOperator(
        task_id='trigger_graph',
        trigger_dag_id='refresh_graph_index',
        wait_for_completion=False
    )

    verify >> trigger_embeddings
    verify >> trigger_graph

