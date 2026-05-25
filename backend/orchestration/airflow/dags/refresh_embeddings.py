from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta

def run_es_indexing():
    import asyncio
    from services.ai.elasticsearch.es_indexer import ElasticIndexer
    indexer = ElasticIndexer()
    asyncio.run(indexer.run_full_index())

def run_pgvector_indexing():
    import asyncio
    from services.ai.embeddings.indexer import EmbeddingIndexer
    indexer = EmbeddingIndexer()
    asyncio.run(indexer.run_full_index())

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
    'refresh_embeddings',
    default_args=default_args,
    description='Re-index data to Elasticsearch and pgvector',
    schedule=None,
    catchup=False,
    tags=['ai', 'rag', 'intelligence']
) as dag:

    es_index_task = PythonOperator(
        task_id='es_index',
        python_callable=run_es_indexing
    )

    pgvector_index_task = PythonOperator(
        task_id='pgvector_index',
        python_callable=run_pgvector_indexing
    )

    [es_index_task, pgvector_index_task]
