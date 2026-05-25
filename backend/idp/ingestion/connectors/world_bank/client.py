"""World Bank API client — returns EconomicIndicator dataclass instances."""

from __future__ import annotations

from datetime import datetime, timezone

import wbgapi as wb

from idp.core.logging import get_logger
from idp.core.models import EconomicIndicator

logger = get_logger(__name__)

DEFAULT_COUNTRIES = ["VNM", "THA", "IDN", "PHL", "MYS", "SGP", "CHN", "USA", "JPN", "KOR"]

DEFAULT_INDICATORS = [
    "NY.GDP.MKTP.CD", "NY.GDP.MKTP.KD.ZG", "NY.GDP.PCAP.CD", "NY.GNP.PCAP.CD",
    "FP.CPI.TOTL.ZG", "FP.CPI.TOTL",
    "SL.UEM.TOTL.ZS", "SL.TLF.TOTL.IN",
    "BX.KLT.DINV.WD.GD.ZS", "NE.EXP.GNFS.ZS", "NE.IMP.GNFS.ZS", "BN.CAB.XOKA.GD.ZS",
    "GC.DOD.TOTL.GD.ZS", "FI.RES.TOTL.CD", "PA.NUS.FCRF",
    "SP.POP.TOTL", "SP.POP.GROW", "SI.POV.GINI",
    "SE.PRM.ENRR", "IT.NET.USER.ZS",
    "EG.USE.ELEC.KH.PC", "EN.ATM.CO2E.KT",
    "NV.AGR.TOTL.ZS", "NV.IND.TOTL.ZS", "NV.SRV.TOTL.ZS",
    "LP.LPI.OVRL.XQ", "TM.TAX.MRCH.SM.AR", "IT.CEL.SETS.P2",
    "IT.NET.BBND.P2", "GB.XPD.RSDV.GD.ZS", "SL.TLF.CACT.FE.ZS", "ST.INT.RCPT.CD",
]

_country_cache: dict[str, str] = {}
_indicator_cache: dict[str, str] = {}


class WorldBankAPIClient:
    """Static methods for fetching World Bank Open Data via wbgapi."""

    @staticmethod
    def fetch_indicators(
        country_codes: list[str] | None = None,
        indicator_codes: list[str] | None = None,
        start_year: int = 2000,
        end_year: int = 2024,
    ) -> list[EconomicIndicator]:
        countries = country_codes or DEFAULT_COUNTRIES
        indicators = indicator_codes or DEFAULT_INDICATORS
        now = datetime.now(timezone.utc)
        results: list[EconomicIndicator] = []

        for entry in wb.data.fetch(
            series=indicators,
            economy=countries,
            time=range(start_year, end_year + 1),
        ):
            val = entry.get("value")
            if val is None:
                continue
            results.append(EconomicIndicator(
                country_code=entry["economy"],
                country_name=WorldBankAPIClient._country_name(entry["economy"]),
                indicator_code=entry["series"],
                indicator_name=WorldBankAPIClient._indicator_name(entry["series"]),
                year=int(entry["time"].replace("YR", "")),
                value=float(val),
                _ingested_at=now,
                _source="world_bank",
            ))
        logger.info("Fetched %d indicators (%d countries, %d series)", len(results), len(countries), len(indicators))
        return results

    @staticmethod
    def _country_name(code: str) -> str:
        if code not in _country_cache:
            try:
                _country_cache[code] = wb.economy.get(code).get("value", code)
            except Exception:
                _country_cache[code] = code
        return _country_cache[code]

    @staticmethod
    def _indicator_name(code: str) -> str:
        if code not in _indicator_cache:
            try:
                _indicator_cache[code] = wb.series.get(code).get("value", code)
            except Exception:
                _indicator_cache[code] = code
        return _indicator_cache[code]
