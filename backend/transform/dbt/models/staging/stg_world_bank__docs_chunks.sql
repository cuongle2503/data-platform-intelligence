SELECT
    chunk_id,
    chunk_index,
    text,
    doc_id,
    title,
    display_date,
    doc_type,
    countries,
    topics,
    language,
    _ingested_at                              AS ingested_at,
    _source                                    AS source
FROM read_parquet('s3://bronze/world_bank_docs/chunks/chunks.parquet')
WHERE text IS NOT NULL
  AND LENGTH(text) > 0
