"""Shared data models as dataclasses. Documents the shape of data flowing through the pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class EconomicIndicator:
    country_code: str
    country_name: str
    indicator_code: str
    indicator_name: str
    year: int
    value: float | None
    _ingested_at: datetime | None = None
    _source: str = "world_bank"


@dataclass
class Document:
    doc_id: str
    title: str
    abstract: str
    display_date: str
    doc_type: str
    pdf_url: str
    countries: str
    topics: str
    language: str
    _ingested_at: datetime | None = None
    _source: str = "world_bank_docs"


@dataclass
class TextChunk:
    chunk_id: str
    chunk_index: int
    text: str
    doc_id: str
    title: str = ""
    doc_type: str = ""
    countries: str = ""
    topics: str = ""
    _ingested_at: datetime | None = None
