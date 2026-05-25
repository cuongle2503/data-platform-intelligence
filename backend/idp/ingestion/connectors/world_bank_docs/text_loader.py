"""Fetch server-extracted text from World Bank document /text/ endpoint."""

from __future__ import annotations

import time

import requests

from idp.core.logging import get_logger

logger = get_logger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36",
    "Accept": "text/plain,*/*",
}

RETRYABLE_STATUS = {403, 429, 502, 503, 504}
MAX_ATTEMPTS = 4
BACKOFF_BASE = 2.0


class TextLoader:
    """Fetch World Bank server-extracted text via the /text/ endpoint.

    Server-side extraction produces ~70% more characters than local PDF
    parsing, with correct whitespace.
    """

    @staticmethod
    def _txt_url(pdf_url: str) -> str | None:
        if "/pdf/" not in pdf_url or not pdf_url.lower().endswith(".pdf"):
            return None
        return pdf_url.replace("http://", "https://").replace("/pdf/", "/text/")[:-4] + ".txt"

    @staticmethod
    def fetch(pdf_url: str, session: requests.Session | None = None) -> str | None:
        if not pdf_url:
            return None
        txt_url = TextLoader._txt_url(pdf_url)
        if not txt_url:
            return None

        sess = session or requests
        last_err = ""
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                resp = sess.get(txt_url, timeout=60, headers=HEADERS)
                if resp.status_code == 200:
                    ct = resp.headers.get("content-type", "").lower()
                    if "text" not in ct:
                        logger.debug("non-text content-type: %s", ct)
                        break
                    return resp.text
                if resp.status_code in RETRYABLE_STATUS and attempt < MAX_ATTEMPTS:
                    time.sleep(BACKOFF_BASE * attempt)
                    last_err = f"HTTP {resp.status_code}"
                    continue
                last_err = f"HTTP {resp.status_code}"
                break
            except requests.RequestException as e:
                last_err = str(e)
                if attempt < MAX_ATTEMPTS:
                    time.sleep(BACKOFF_BASE * attempt)
                    continue
                break

        logger.warning("Text fetch failed: %s — %s", txt_url, last_err)
        return None
