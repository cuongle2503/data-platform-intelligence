"""Neo4j graph schema for data lineage and economic relationships."""

from __future__ import annotations

# Cypher queries to create constraints and indexes
CONSTRAINTS = [
    "CREATE CONSTRAINT country_code IF NOT EXISTS FOR (c:Country) REQUIRE c.code IS UNIQUE;",
    "CREATE CONSTRAINT indicator_code IF NOT EXISTS FOR (i:Indicator) REQUIRE i.code IS UNIQUE;",
    "CREATE CONSTRAINT category_name IF NOT EXISTS FOR (ic:IndicatorCategory) REQUIRE ic.name IS UNIQUE;",
    "CREATE CONSTRAINT doc_id IF NOT EXISTS FOR (d:Document) REQUIRE d.doc_id IS UNIQUE;",
    "CREATE CONSTRAINT table_name IF NOT EXISTS FOR (dt:DataTable) REQUIRE dt.name IS UNIQUE;",
]

INDEXES = [
    "CREATE INDEX column_fqn IF NOT EXISTS FOR (dc:DataColumn) ON (dc.table_name, dc.column_name);",
    "CREATE INDEX country_name IF NOT EXISTS FOR (c:Country) ON (c.name);",
    "CREATE INDEX indicator_name IF NOT EXISTS FOR (i:Indicator) ON (i.name);",
]
