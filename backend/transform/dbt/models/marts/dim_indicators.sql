WITH seed AS (
    SELECT * FROM {{ ref('seed_indicators') }}
),

-- Derive source_system from indicator context: world_bank for now (NSO, FRED later)
enriched AS (
    SELECT
        indicator_code,
        indicator_name,
        category,
        unit,
        frequency,
        description,
        'world_bank' AS source_system
    FROM seed
)

SELECT
    ROW_NUMBER() OVER (ORDER BY indicator_code)     AS indicator_key,
    indicator_code,
    indicator_name,
    source_system,
    category,
    unit,
    frequency,
    description
FROM enriched
