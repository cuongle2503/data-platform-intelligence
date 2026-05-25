"""WBDocsConnector — ETL for World Bank document metadata + full-text → MinIO Bronze."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone

import pandas as pd
import requests

from idp.core.config import settings
from idp.ingestion.base import AbstractConnector
from idp.ingestion.connectors.world_bank_docs.chunker import chunk_text
from idp.ingestion.connectors.world_bank_docs.text_loader import TextLoader
from idp.ingestion.connectors.world_bank_docs.wds_client import WDSClient
from idp.ingestion.services.minio import MinioService


class WBDocsConnector(AbstractConnector):
    """Search WDS, fetch metadata, optionally fetch full-text and chunk."""

    def __init__(self, minio: MinioService | None = None, full_text: bool = False) -> None:
        super().__init__(minio)
        self.full_text = full_text

    def extract(self, **kwargs: object) -> list:
        self.logger.info("Searching WDS...")
        docs = WDSClient.search()
        self.logger.info("Found %d documents", len(docs))
        if not docs:
            raise RuntimeError("No documents found")
        return docs

    def transform(self, raw: list) -> pd.DataFrame:
        now = datetime.now(timezone.utc)
        for d in raw:
            d._ingested_at = now
        return pd.DataFrame([asdict(r) for r in raw])

    def _load_multiple(self, df: pd.DataFrame, **kwargs: object) -> None:
        tmp_dir = settings.tmp_dir / "world_bank_docs"

        # Metadata
        meta_local = tmp_dir / "metadata" / "documents.parquet"
        self.load(df, meta_local, "bronze", "world_bank_docs/metadata/documents.parquet")
        self.logger.info("Metadata: %d docs → bronze/world_bank_docs/metadata/", len(df))

        if not self.full_text:
            return

        # Full-text
        self.logger.info("Fetching full-text and chunking...")
        session = requests.Session()
        try:
            fetched = 0
            all_chunks: list[dict] = []
            now = datetime.now(timezone.utc)

            for i, row in df.iterrows():
                pdf_url = row.get("pdf_url", "")
                if not pdf_url:
                    continue
                self.logger.info("[%d/%d] %s", i + 1, len(df), row["doc_id"])
                text = TextLoader.fetch(str(pdf_url), session=session)
                if not text:
                    continue
                fetched += 1
                chunks = chunk_text(text, doc_id=str(row["doc_id"]))
                for ch in chunks:
                    ch.update({
                        "doc_id": row["doc_id"],
                        "title": row["title"],
                        "display_date": row["display_date"],
                        "doc_type": row["doc_type"],
                        "countries": row["countries"],
                        "topics": row["topics"],
                        "language": row["language"],
                        "_ingested_at": now,
                        "_source": "world_bank_docs",
                    })
                all_chunks.extend(chunks)
        finally:
            session.close()

        self.logger.info("Fetched: %d/%d documents", fetched, len(df))
        if all_chunks:
            df_chunks = pd.DataFrame(all_chunks)
            df_chunks["chunk_index"] = df_chunks["chunk_index"].astype("int64")
            chunks_local = tmp_dir / "chunks" / "chunks.parquet"
            self.load(df_chunks, chunks_local, "bronze", "world_bank_docs/chunks/chunks.parquet")
            self.logger.info(
                "Chunks: %d from %d docs → bronze/world_bank_docs/chunks/",
                len(df_chunks), df_chunks["doc_id"].nunique(),
            )
        else:
            self.logger.warning("No chunks produced")


def main() -> None:
    parser = argparse.ArgumentParser(description="World Bank Documents → MinIO Bronze")
    parser.add_argument(
        "--full-text", action="store_true", default=False,
        help="Also fetch server-extracted text and produce chunks parquet",
    )
    args = parser.parse_args()

    with MinioService() as minio:
        connector = WBDocsConnector(minio, full_text=args.full_text)
        connector.run()
    print("Done.")


if __name__ == "__main__":
    main()
