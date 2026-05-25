from __future__ import annotations
from services.shared.database import DatabasePool
from services.shared.logging import get_logger

logger = get_logger(__name__)

class StructuredRetriever:
    @staticmethod
    async def get_fact_value(country_code: str, indicator_code: str, year: int | None = None):
        """Query fact table for a specific value."""
        pool = DatabasePool.get_pool()
        async with pool.acquire() as conn:
            if year is None:
                query = """
                    SELECT f.value, i.unit, c.country_name, i.indicator_name,
                           EXTRACT(YEAR FROM f.period_start)::int AS year
                    FROM gold.fact_economic_indicators f
                    JOIN gold.dim_countries c ON f.country_key = c.country_key
                    JOIN gold.dim_indicators i ON f.indicator_key = i.indicator_key
                    WHERE c.country_code = $1 AND i.indicator_code = $2
                    ORDER BY f.period_start DESC
                    LIMIT 1;
                """
                return await conn.fetchrow(query, country_code, indicator_code)

            query = """
                SELECT f.value, i.unit, c.country_name, i.indicator_name,
                       EXTRACT(YEAR FROM f.period_start)::int AS year
                FROM gold.fact_economic_indicators f
                JOIN gold.dim_countries c ON f.country_key = c.country_key
                JOIN gold.dim_indicators i ON f.indicator_key = i.indicator_key
                WHERE c.country_code = $1 AND i.indicator_code = $2
                  AND EXTRACT(YEAR FROM f.period_start)::int = $3
                LIMIT 1;
            """
            return await conn.fetchrow(query, country_code, indicator_code, year)

    @staticmethod
    async def get_timeseries(country_code: str, indicator_code: str):
        """Query all available years for a specific indicator and country."""
        pool = DatabasePool.get_pool()
        async with pool.acquire() as conn:
            query = """
                SELECT f.value, i.unit, c.country_name, i.indicator_name,
                       EXTRACT(YEAR FROM f.period_start)::int AS year
                FROM gold.fact_economic_indicators f
                JOIN gold.dim_countries c ON f.country_key = c.country_key
                JOIN gold.dim_indicators i ON f.indicator_key = i.indicator_key
                WHERE c.country_code = $1 AND i.indicator_code = $2
                ORDER BY f.period_start ASC;
            """
            return await conn.fetch(query, country_code, indicator_code)
