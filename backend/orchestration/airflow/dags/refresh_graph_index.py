from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta

def run_graph_build():
    import asyncio
    from services.ai.graph.builder import GraphBuilder
    builder = GraphBuilder()
    asyncio.run(builder.build_all())

default_args = {
    'owner': 'idp',
    'depends_on_past': False,
    'start_date': datetime(2025, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'refresh_graph_index',
    default_args=default_args,
    description='Rebuild Neo4j graph from PostgreSQL Gold data',
    schedule=None,
    catchup=False,
    tags=['ai', 'rag', 'intelligence', 'graph']
) as dag:

    graph_build_task = PythonOperator(
        task_id='graph_build',
        python_callable=run_graph_build
    )
