-- GDP absolute values (current USD, per capita, etc.) should never be ≤ 0
-- GDP growth rate (NY.GDP.MKTP.KD.ZG) CAN be negative (recession), so exclude it
WITH gdp_absolute_indicators AS (
    SELECT indicator_key
    FROM {{ ref('dim_indicators') }}
    WHERE indicator_code IN ('NY.GDP.MKTP.CD', 'NY.GDP.PCAP.CD', 'NY.GNP.PCAP.CD')
)

SELECT *
FROM {{ ref('fact_economic_indicators') }} f
JOIN gdp_absolute_indicators g ON f.indicator_key = g.indicator_key
WHERE f.value <= 0
