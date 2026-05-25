"""DAG: Run dbt transform pipeline (seed → run → test).

Triggered by upstream ingestion DAGs via TriggerDagRunOperator.
"""
from __future__ import annotations

from datetime import datetime

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator

from idp.core.config import settings
from idp.orchestration.dag_utils import default_dag_args, ensure_duckdb_secret

DAG_ID = "run_dbt_transform"
DBT_DIR = str(settings.dbt_dir)


def _setup_duckdb(**ctx):
    ensure_duckdb_secret(str(settings.duckdb_path))


with DAG(
    dag_id=DAG_ID,
    default_args=default_dag_args(retries=1, retry_delay_minutes=2),
    description="Run dbt seed → run → test on DuckDB after ingestion completes",
    schedule=None,
    start_date=datetime(2024, 1, 1),
    max_active_runs=1,
    catchup=False,
    tags=["transform", "dbt"],
) as dag:

    setup_duckdb = PythonOperator(
        task_id="setup_duckdb_secret",
        python_callable=_setup_duckdb,
    )

    dbt_seed = BashOperator(
        task_id="dbt_seed",
        bash_command=f"cd {DBT_DIR} && dbt seed --profiles-dir .",
    )

    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command=f"cd {DBT_DIR} && dbt run --profiles-dir .",
    )

    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=f"cd {DBT_DIR} && dbt test --profiles-dir .",
    )

    trigger_export = TriggerDagRunOperator(
        task_id="trigger_export",
        trigger_dag_id="export_gold_to_postgres",
    )

    setup_duckdb >> dbt_seed >> dbt_run >> dbt_test >> trigger_export
