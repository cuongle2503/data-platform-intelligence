FROM apache/airflow:3.0.6-python3.12

USER airflow

COPY --chown=airflow:root entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

RUN pip install --no-cache-dir \
    dbt-core \
    dbt-duckdb \
    duckdb \
    wbgapi \
    pandas \
    pyarrow \
    boto3 \
    psycopg2-binary \
    pydantic-settings \
    neo4j \
    elasticsearch \
    google-genai \
    asyncpg \
    structlog

# Pre-cached DuckDB extensions (skipped — build extensions/ dir separately)
# COPY --chown=airflow:root extensions/ /home/airflow/.duckdb/extensions/
