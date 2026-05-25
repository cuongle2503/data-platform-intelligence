"""PostgresExportService — export Gold mart tables from DuckDB to PostgreSQL.

Usage:
    python -m idp.transform.export           # CLI
    service = PostgresExportService()         # programmatic (DAG)
    service.export_tables()
"""

from __future__ import annotations

import sys
import time

import duckdb

from idp.core.config import settings
from idp.core.logging import get_logger

logger = get_logger(__name__)

TABLES = [
    ("main_gold.dim_countries", "gold.dim_countries"),
    ("main_gold.dim_indicators", "gold.dim_indicators"),
    ("main_gold.dim_dates", "gold.dim_dates"),
    ("main_gold.fact_economic_indicators", "gold.fact_economic_indicators"),
]


class PostgresExportService:
    """Export Gold mart tables from DuckDB to PostgreSQL gold schema."""

    def __init__(
        self,
        duckdb_path: str | None = None,
        pg_conn_str: str | None = None,
    ) -> None:
        self.duckdb_path = duckdb_path or str(settings.duckdb_path)
        self.pg_conn_str = pg_conn_str or settings.postgres_conn_str

    def export_tables(self, max_retries: int = 3) -> None:
        conn = duckdb.connect(self.duckdb_path)
        try:
            conn.execute("LOAD postgres;")
        except Exception:
            conn.execute("INSTALL postgres; LOAD postgres;")

        for attempt in range(1, max_retries + 1):
            try:
                conn.execute(f"ATTACH '{self.pg_conn_str}' AS pg_db (TYPE postgres)")
                logger.info("Connected to PostgreSQL")
                break
            except Exception as e:
                if attempt == max_retries:
                    raise RuntimeError(
                        f"Failed to connect after {max_retries} attempts: {e}"
                    ) from e
                logger.warning("Connection attempt %d failed, retrying in 3s... (%s)", attempt, e)
                time.sleep(3)

        for duck_src, pg_tgt in TABLES:
            count = conn.execute(f"SELECT count(*) FROM {duck_src}").fetchone()[0]
            conn.execute(f"CREATE OR REPLACE TABLE pg_db.{pg_tgt} AS SELECT * FROM {duck_src}")
            logger.info("  %s: %d rows exported", pg_tgt, count)

        conn.execute("DETACH pg_db")
        conn.close()
        logger.info("Export complete.")


def main() -> None:
    try:
        PostgresExportService().export_tables()
    except Exception:
        logger.exception("Export failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
