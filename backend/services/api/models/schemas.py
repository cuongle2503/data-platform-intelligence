from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field

class IndicatorResponse(BaseModel):
    indicator_code: str
    indicator_name: str
    country_code: str
    year: int
    value: float
    category: Optional[str] = None
    source_system: str

class IndicatorListResponse(BaseModel):
    indicator_code: str
    indicator_name: str
    category: Optional[str] = None
    unit: Optional[str] = None
    description: Optional[str] = None

class CountryResponse(BaseModel):
    country_code: str
    country_name: str
    region: Optional[str] = None
    income_group: Optional[str] = None
