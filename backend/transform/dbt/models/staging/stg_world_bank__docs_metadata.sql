SELECT
    TRIM(doc_id)                              AS doc_id,
    TRIM(title)                               AS title,
    TRIM(abstract)                            AS abstract,
    TRIM(display_date)                        AS display_date,
    TRIM(doc_type)                            AS doc_type,
    TRIM(pdf_url)                             AS pdf_url,
    TRIM(countries)                           AS countries,
    TRIM(topics)                              AS topics,
    TRIM(language)                            AS language,
    _ingested_at                              AS ingested_at,
    _source                                   AS source
FROM read_parquet('s3://bronze/world_bank_docs/metadata/documents.parquet')
WHERE doc_id IS NOT NULL
