"""WorldBankConnector — ETL for World Bank economic indicators → MinIO Bronze."""

from __future__ import annotations

import argparse
from dataclasses import asdict

import pandas as pd

from idp.core.config import settings
from idp.ingestion.base import AbstractConnector
from idp.ingestion.connectors.world_bank.client import (
    DEFAULT_COUNTRIES,
    DEFAULT_INDICATORS,
    WorldBankAPIClient,
)
from idp.ingestion.services.minio import MinioService


class WorldBankConnector(AbstractConnector):
    """Fetch World Bank indicators, partition by year, upload to MinIO Bronze."""

    def extract(self, **kwargs: object) -> list:
        return WorldBankAPIClient.fetch_indicators(
            country_codes=kwargs.get("country_codes"),        # type: ignore[arg-type]
            indicator_codes=kwargs.get("indicator_codes"),    # type: ignore[arg-type]
            start_year=int(kwargs.get("start_year", 2020)),   # type: ignore[arg-type]
            end_year=int(kwargs.get("end_year", 2024)),       # type: ignore[arg-type]
        )

    def transform(self, raw: list) -> pd.DataFrame:
        if not raw:
            return pd.DataFrame()
        df = pd.DataFrame([asdict(r) for r in raw])
        df["year"] = df["year"].astype("int64")
        self.logger.info(
            "%d rows | %d indicators | %d countries",
            len(df), df["indicator_code"].nunique(), df["country_code"].nunique(),
        )
        return df

    def _load_multiple(self, df: pd.DataFrame, **_: object) -> None:
        tmp_dir = settings.tmp_dir / "world_bank"
        for year in sorted(df["year"].unique()):
            year_df = df[df["year"] == year]
            local_path = tmp_dir / f"year={year}" / "data.parquet"
            key = f"world_bank/indicators/year={year}/data.parquet"
            self.load(year_df, local_path, "bronze", key)
            size_kb = local_path.stat().st_size / 1024 if local_path.exists() else 0
            self.logger.info("  year=%s: %d rows, %.1f KB → bronze/%s", year, len(year_df), size_kb, key)


def main() -> None:
    parser = argparse.ArgumentParser(description="World Bank indicators → MinIO Bronze")
    parser.add_argument("--start-year", type=int, default=2020)
    parser.add_argument("--end-year", type=int, default=2024)
    parser.add_argument("--countries", nargs="*", default=DEFAULT_COUNTRIES)
    parser.add_argument("--indicators", nargs="*", default=DEFAULT_INDICATORS)
    args = parser.parse_args()

    with MinioService() as minio:
        connector = WorldBankConnector(minio)
        connector.run(
            country_codes=args.countries,
            indicator_codes=args.indicators,
            start_year=args.start_year,
            end_year=args.end_year,
        )
    print("Done.")


if __name__ == "__main__":
    main()
