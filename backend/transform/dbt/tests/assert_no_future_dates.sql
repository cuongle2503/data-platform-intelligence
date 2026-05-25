-- No fact rows should reference dates beyond today
SELECT *
FROM {{ ref('fact_economic_indicators') }} f
JOIN {{ ref('dim_dates') }} d ON f.date_key = d.date_key
WHERE d.full_date > current_date
