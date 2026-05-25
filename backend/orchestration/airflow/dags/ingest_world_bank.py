"""DAG: World Bank Open Data ingestion → MinIO Bronze.

Schedule: monthly (day 1, 06:00 ICT).
"""
from __future__ import annotations

from datetime import datetime

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator

from idp.orchestration.dag_utils import (
    create_minio_health_sensor,
    default_dag_args,
    verify_minio_object,
)

DAG_ID = "ingest_world_bank"


def _verify_output(**ctx):
    dag_run = ctx["dag_run"]
    exec_date = dag_run.logical_date or dag_run.run_after
    year = exec_date.year if exec_date.month >= 7 else exec_date.year - 1
    verify_minio_object(
        bucket="bronze",
        key=f"world_bank/indicators/year={year}/data.parquet",
        label="World Bank indicators",
    )


with DAG(
    dag_id=DAG_ID,
    default_args=default_dag_args(retries=3, retry_delay_minutes=5),
    description="Ingest World Bank economic indicators → MinIO Bronze",
    schedule="@monthly",
    start_date=datetime(2024, 1, 1),
    max_active_runs=1,
    catchup=False,
    tags=["ingestion", "world_bank"],
) as dag:

    check_minio = create_minio_health_sensor()

    run_ingestion = BashOperator(
        task_id="run_ingestion",
        bash_command=(
            "{% set ref_date = dag_run.logical_date or dag_run.run_after %} "
            "python -m idp.ingestion.connectors.world_bank.connector "
            "--start-year {{ (ref_date.year - 1) if ref_date.month < 7 else ref_date.year }} "
            "--end-year {{ (ref_date.year - 1) if ref_date.month < 7 else ref_date.year }}"
        ),
    )

    verify_output = PythonOperator(
        task_id="verify_output",
        python_callable=_verify_output,
    )

    trigger_transform = TriggerDagRunOperator(
        task_id="trigger_dbt_transform",
        trigger_dag_id="run_dbt_transform",
    )

    check_minio >> run_ingestion >> verify_output >> trigger_transform
