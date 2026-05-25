WITH seed AS (
    SELECT * FROM {{ ref('seed_countries') }}
),

-- Enrich with World Bank region/income metadata from staging data
wb_regions AS (
    SELECT DISTINCT
        country_code,
        country_name
    FROM {{ ref('stg_world_bank__indicators') }}
)

SELECT
    ROW_NUMBER() OVER (ORDER BY s.country_code)     AS country_key,
    s.country_code,
    COALESCE(s.country_name, w.country_name)        AS country_name,
    s.region,
    s.income_group,
    CAST(s.is_asean AS BOOLEAN)                     AS is_asean,
    CAST(s.is_primary AS BOOLEAN)                   AS is_primary
FROM seed s
LEFT JOIN wb_regions w ON s.country_code = w.country_code
