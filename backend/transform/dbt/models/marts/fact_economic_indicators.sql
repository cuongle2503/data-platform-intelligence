WITH indicators AS (
    SELECT * FROM {{ ref('stg_world_bank__indicators') }}
)

SELECT
    di.indicator_key,
    dc.country_key,
    dd.date_key,
    MAKE_DATE(i.year, 1, 1)                        AS period_start,
    MAKE_DATE(i.year, 12, 31)                      AS period_end,
    i.value,
    'world_bank'                                    AS source_system,
    i.ingested_at                                   AS loaded_at
FROM indicators i
INNER JOIN {{ ref('dim_countries') }} dc
    ON i.country_code = dc.country_code
INNER JOIN {{ ref('dim_indicators') }} di
    ON i.indicator_code = di.indicator_code
    AND di.source_system = 'world_bank'
INNER JOIN {{ ref('dim_dates') }} dd
    ON dd.full_date = MAKE_DATE(i.year, 1, 1)
