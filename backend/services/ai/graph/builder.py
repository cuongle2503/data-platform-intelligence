from __future__ import annotations

import asyncpg
from neo4j import GraphDatabase

from services.shared.config import settings
from services.shared.database import DatabasePool
from services.shared.logging import get_logger
from services.ai.graph.schema import CONSTRAINTS, INDEXES

logger = get_logger(__name__)

class GraphBuilder:
    def __init__(self):
        self.driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password)
        )

    def close(self):
        self.driver.close()

    def run(self, func):
        """Execute a function in a Neo4j driver session."""
        with self.driver.session() as session:
            return session.execute_write(func)

    def init_schema(self, tx):
        """Create constraints and indexes."""
        for stmt in CONSTRAINTS + INDEXES:
            try:
                tx.run(stmt)
            except Exception as e:
                error_str = str(e)
                if "already exists" not in error_str and "EquivalentSchemaRuleAlreadyExists" not in error_str:
                    logger.warning("Schema creation issue", query=stmt, error=error_str)

    async def build_countries(self):
        """Ingest countries from PostgreSQL."""
        pool = DatabasePool.get_pool()
        async with pool.acquire() as conn:
            records = await conn.fetch(
                "SELECT country_code, country_name, region, income_group FROM gold.dim_countries"
            )

        def ingest(tx):
            for r in records:
                tx.run(
                    """MERGE (c:Country {code: $code})
                       SET c.name = $name, c.region = $region, c.income_group = $income_group""",
                    code=r["country_code"], name=r["country_name"],
                    region=r["region"] or "", income_group=r["income_group"] or ""
                )
            return len(records)

        count = self.run(ingest)
        logger.info(f"Ingested {count} countries into graph")
        return count

    async def build_indicators(self):
        """Ingest indicators from PostgreSQL."""
        pool = DatabasePool.get_pool()
        async with pool.acquire() as conn:
            records = await conn.fetch(
                "SELECT indicator_code, indicator_name, category, source_system, unit, description FROM gold.dim_indicators"
            )

        def ingest(tx):
            for r in records:
                tx.run(
                    """MERGE (i:Indicator {code: $code})
                       SET i.name = $name, i.source_system = $source,
                           i.unit = $unit, i.description = $description""",
                    code=r["indicator_code"], name=r["indicator_name"],
                    source=r["source_system"] or "", unit=r["unit"] or "",
                    description=r["description"] or ""
                )
                if r["category"]:
                    tx.run(
                        """MERGE (ic:IndicatorCategory {name: $cat})
                           WITH ic
                           MATCH (i:Indicator {code: $code})
                           MERGE (i)-[:BELONGS_TO]->(ic)""",
                        cat=r["category"], code=r["indicator_code"]
                    )
            return len(records)

        count = self.run(ingest)
        logger.info(f"Ingested {count} indicators into graph")
        return count

    async def build_country_indicator_edges(self):
        """Link countries to indicators via fact table."""
        pool = DatabasePool.get_pool()
        async with pool.acquire() as conn:
            records = await conn.fetch(
                """SELECT DISTINCT c.country_code, i.indicator_code
                   FROM gold.fact_economic_indicators f
                   JOIN gold.dim_countries c ON f.country_key = c.country_key
                   JOIN gold.dim_indicators i ON f.indicator_key = i.indicator_key"""
            )

        def link(tx):
            for r in records:
                tx.run(
                    """MATCH (c:Country {code: $country_code})
                       MATCH (i:Indicator {code: $indicator_code})
                       MERGE (c)-[:HAS_INDICATOR]->(i)""",
                    country_code=r["country_code"], indicator_code=r["indicator_code"]
                )
            return len(records)

        count = self.run(link)
        logger.info(f"Created {count} country-indicator edges")
        return count

    async def build_data_lineage(self):
        """Build data lineage: Indicator -> DataTable -> DataColumn."""
        tables = [
            "raw_world_bank_indicators",
            "stg_world_bank__indicators",
            "dim_indicators",
            "dim_countries",
            "dim_dates",
            "fact_economic_indicators"
        ]
        columns = {
            "raw_world_bank_indicators": ["country_code", "country_name", "indicator_code", "indicator_name", "year", "value", "_ingested_at", "_source"],
            "stg_world_bank__indicators": ["country_code", "country_name", "indicator_code", "indicator_name", "year", "value", "ingested_at"],
            "dim_indicators": ["indicator_key", "indicator_code", "indicator_name", "source_system", "category", "unit", "frequency", "description"],
            "dim_countries": ["country_key", "country_code", "country_name", "region", "income_group", "is_asean", "is_primary"],
            "dim_dates": ["date_key", "full_date", "year", "quarter", "month"],
            "fact_economic_indicators": ["indicator_key", "country_key", "date_key", "value", "source_system", "loaded_at"]
        }

        def build(tx):
            for t in tables:
                tx.run("MERGE (dt:DataTable {name: $name})", name=t)
            for t_name, cols in columns.items():
                for c in cols:
                    tx.run(
                        """MATCH (dt:DataTable {name: $t})
                           MERGE (dt)-[:CONTAINS]->(dc:DataColumn {table_name: $t, column_name: $c})""",
                        t=t_name, c=c
                    )
            return len(tables)

        count = self.run(build)
        logger.info(f"Created data lineage graph with {count} tables")

    async def build_documents(self):
        """Ingest document metadata from local Parquet."""
        import pandas as pd
        from pathlib import Path
        path = Path("/home/pc/my-projects/data-platform-intelligent/backend/tmp/world_bank_docs/metadata/documents.parquet")
        if not path.exists():
            logger.warning("Documents parquet not found, skipping graph ingestion")
            return 0

        df = pd.read_parquet(path)
        records = df.to_dict("records")

        def ingest(tx):
            for r in records:
                tx.run(
                    """MERGE (d:Document {doc_id: $doc_id})
                       SET d.title = $title, d.doc_type = $doc_type,
                           d.abstract = $abstract, d.topics = $topics""",
                    doc_id=r["doc_id"], title=r["title"],
                    doc_type=r.get("doc_type") or "",
                    abstract=r.get("abstract") or "",
                    topics=r.get("topics") or ""
                )
                # Link to countries (simple keyword match)
                if r["countries"]:
                    countries = [c.strip() for c in r["countries"].split(",")]
                    tx.run(
                        """MATCH (d:Document {doc_id: $doc_id})
                           MATCH (c:Country) WHERE c.name IN $countries OR c.code IN $countries
                           MERGE (d)-[:ABOUT]->(c)""",
                        doc_id=r["doc_id"], countries=countries
                    )
            return len(records)

        count = self.run(ingest)
        logger.info(f"Ingested {count} documents into graph")
        return count

    async def build_all(self):
        """Execute full graph build pipeline."""
        await DatabasePool.connect()
        try:
            self.run(self.init_schema)
            await self.build_countries()
            await self.build_indicators()
            await self.build_country_indicator_edges()
            await self.build_data_lineage()
            await self.build_documents()
        finally:
            await DatabasePool.disconnect()
            self.close()
