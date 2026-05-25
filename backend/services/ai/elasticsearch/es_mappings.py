from __future__ import annotations

INDICATORS_MAPPING = {
    "mappings": {
        "properties": {
            "indicator_code": {"type": "keyword"},
            "indicator_name": {
                "type": "text",
                "analyzer": "standard",
                "fields": {
                    "keyword": {"type": "keyword"}
                }
            },
            "category": {"type": "keyword"},
            "description": {"type": "text", "analyzer": "standard"}
        }
    }
}

DOCUMENTS_MAPPING = {
    "mappings": {
        "properties": {
            "doc_id": {"type": "keyword"},
            "title": {"type": "text", "analyzer": "standard"},
            "abstract": {"type": "text", "analyzer": "standard"},
            "doc_type": {"type": "keyword"},
            "countries": {"type": "text", "analyzer": "standard"},
            "topics": {"type": "text", "analyzer": "standard"},
            "language": {"type": "keyword"}
        }
    }
}

CHUNKS_MAPPING = {
    "mappings": {
        "properties": {
            "chunk_id": {"type": "keyword"},
            "doc_id": {"type": "keyword"},
            "text": {"type": "text", "analyzer": "standard"},
            "title": {"type": "text"}
        }
    }
}
