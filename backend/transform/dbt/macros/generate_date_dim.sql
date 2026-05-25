{% macro generate_date_dim(start_date, end_date) %}
WITH date_series AS (
    SELECT UNNEST(generate_series(
        DATE '{{ start_date }}',
        DATE '{{ end_date }}',
        INTERVAL 1 DAY
    )) AS full_date
)
SELECT
    CAST(strftime(full_date, '%Y%m%d') AS INTEGER) AS date_key,
    full_date,
    EXTRACT(YEAR FROM full_date)                   AS year,
    EXTRACT(QUARTER FROM full_date)                AS quarter,
    EXTRACT(MONTH FROM full_date)                  AS month,
    CASE EXTRACT(MONTH FROM full_date)
        WHEN 1 THEN 'January'   WHEN 2 THEN 'February'  WHEN 3 THEN 'March'
        WHEN 4 THEN 'April'     WHEN 5 THEN 'May'       WHEN 6 THEN 'June'
        WHEN 7 THEN 'July'      WHEN 8 THEN 'August'    WHEN 9 THEN 'September'
        WHEN 10 THEN 'October'  WHEN 11 THEN 'November' WHEN 12 THEN 'December'
    END                                             AS month_name,
    EXTRACT(DOW FROM full_date) + 1                AS day_of_week,
    CASE WHEN EXTRACT(DOW FROM full_date) IN (0, 6) THEN true ELSE false END AS is_weekend,
    false                                           AS is_vietnam_holiday,
    EXTRACT(YEAR FROM full_date)                    AS fiscal_year_vn
FROM date_series
ORDER BY full_date
{% endmacro %}
