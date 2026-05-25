"""DAG: World Bank Documents metadata + full-text ingestion → MinIO Bronze.

Schedule: monthly (day 2, 06:00 ICT).
Full-text only runs on quarter-end months (Mar, Jun, Sep, Dec).
"""
from __future__ import annotations

from datetime import datetime

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator, BranchPythonOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator

from idp.orchestration.dag_utils import (
    create_minio_health_sensor,
    default_dag_args,
    ensure_empty_chunks_parquet,
    verify_minio_object,
)

DAG_ID = "ingest_world_bank_docs"


def _should_run_fulltext(**ctx) -> str:
    dag_run = ctx["dag_run"]
    exec_date = dag_run.logical_date or dag_run.run_after
    if exec_date.month in (3, 6, 9, 12):
        return "run_fulltext_ingestion"
    return "skip_fulltext"


def _verify_metadata(**ctx):
    verify_minio_object(
        "bronze", "world_bank_docs/metadata/documents.parquet", "WBDocs metadata"
    )


def _verify_chunks(**ctx):
    verify_minio_object(
        "bronze", "world_bank_docs/chunks/chunks.parquet", "WBDocs chunks"
    )


with DAG(
    dag_id=DAG_ID,
    default_args=default_dag_args(retries=3, retry_delay_minutes=5),
    description="Ingest World Bank document metadata + full-text → MinIO Bronze",
    schedule="@monthly",
    start_date=datetime(2024, 1, 1),
    max_active_runs=1,
    catchup=False,
    tags=["ingestion", "world_bank"],
) as dag:

    check_minio = create_minio_health_sensor()

    run_metadata = BashOperator(
        task_id="run_metadata_ingestion",
        bash_command="python -m idp.ingestion.connectors.world_bank_docs.connector",
    )

    branch = BranchPythonOperator(
        task_id="branch_fulltext",
        python_callable=_should_run_fulltext,
    )

    run_fulltext = BashOperator(
        task_id="run_fulltext_ingestion",
        bash_command="python -m idp.ingestion.connectors.world_bank_docs.connector --full-text",
    )

    skip_fulltext = PythonOperator(
        task_id="skip_fulltext",
        python_callable=ensure_empty_chunks_parquet,
    )

    verify_meta = PythonOperator(
        task_id="verify_metadata",
        python_callable=_verify_metadata,
        trigger_rule="none_failed",
    )

    verify_chunks = PythonOperator(
        task_id="verify_chunks",
        python_callable=_verify_chunks,
    )

    check_minio >> run_metadata >> branch
    branch >> run_fulltext >> verify_chunks
    branch >> skip_fulltext
    run_metadata >> verify_meta

    trigger_transform = TriggerDagRunOperator(
        task_id="trigger_dbt_transform",
        trigger_dag_id="run_dbt_transform",
        trigger_rule="none_failed_min_one_success",
    )
    [verify_meta, verify_chunks, skip_fulltext] >> trigger_transform
