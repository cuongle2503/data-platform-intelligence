from __future__ import annotations

from typing import List, Optional

import asyncpg
from fastapi import APIRouter, Depends, Query, HTTPException

from services.shared.database import get_db
from services.api.models.schemas import IndicatorResponse, IndicatorListResponse, CountryResponse

router = APIRouter(prefix="/api", tags=["indicators"])

@router.get("/countries", response_model=List[CountryResponse])
async def get_countries(db: asyncpg.Connection = Depends(get_db)):
    """Get list of available countries."""
    query = """
        SELECT country_code, country_name, region, income_group
        FROM gold.dim_countries
        ORDER BY country_name;
    """
    records = await db.fetch(query)
    return [dict(r) for r in records]

@router.get("/indicators/list", response_model=List[IndicatorListResponse])
async def get_indicators_list(db: asyncpg.Connection = Depends(get_db)):
    """Get list of available economic indicators."""
    query = """
        SELECT indicator_code, indicator_name, category, unit, description
        FROM gold.dim_indicators
        ORDER BY indicator_name;
    """
    records = await db.fetch(query)
    return [dict(r) for r in records]

@router.get("/indicators", response_model=List[IndicatorResponse])
async def get_indicators_data(
    country_code: str = Query(..., description="ISO 3-letter country code"),
    start_year: Optional[int] = Query(None, description="Start year"),
    end_year: Optional[int] = Query(None, description="End year"),
    db: asyncpg.Connection = Depends(get_db)
):
    """Query economic indicators fact data."""
    query = """
        SELECT
            i.indicator_code,
            i.indicator_name,
            c.country_code,
            d.year,
            f.value,
            i.category,
            f.source_system
        FROM gold.fact_economic_indicators f
        JOIN gold.dim_indicators i ON f.indicator_key = i.indicator_key
        JOIN gold.dim_countries c ON f.country_key = c.country_key
        JOIN gold.dim_dates d ON f.date_key = d.date_key
        WHERE c.country_code = $1
    """
    args = [country_code.upper()]

    if start_year:
        query += f" AND d.year >= ${len(args) + 1}"
        args.append(start_year)
    if end_year:
        query += f" AND d.year <= ${len(args) + 1}"
        args.append(end_year)

    query += " ORDER BY i.indicator_code, d.year DESC"

    records = await db.fetch(query, *args)
    return [dict(r) for r in records]

@router.get("/indicators/{indicator_code}", response_model=List[IndicatorResponse])
async def get_indicator_by_code(
    indicator_code: str,
    country_code: Optional[str] = Query("all", description="ISO 3-letter country code or 'all'"),
    db: asyncpg.Connection = Depends(get_db)
):
    """Get time series data for a specific indicator."""
    query = """
        SELECT
            i.indicator_code,
            i.indicator_name,
            c.country_code,
            d.year,
            f.value,
            i.category,
            f.source_system
        FROM gold.fact_economic_indicators f
        JOIN gold.dim_indicators i ON f.indicator_key = i.indicator_key
        JOIN gold.dim_countries c ON f.country_key = c.country_key
        JOIN gold.dim_dates d ON f.date_key = d.date_key
        WHERE i.indicator_code = $1
    """
    args = [indicator_code]

    if country_code and country_code.lower() != "all":
        query += f" AND c.country_code = ${len(args) + 1}"
        args.append(country_code.upper())

    query += " ORDER BY c.country_code, d.year DESC"

    records = await db.fetch(query, *args)
    if not records:
        raise HTTPException(status_code=404, detail="Indicator or data not found")

    return [dict(r) for r in records]
