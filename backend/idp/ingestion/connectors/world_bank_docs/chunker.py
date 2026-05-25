"""Text chunking with paragraph-aware splitting and overlap."""

from __future__ import annotations

import hashlib
import re

_PARA_SPLIT = re.compile(r"\n\s*\n+|\r\n\s*\r\n+")


def _split_paragraphs(text: str, hard_limit: int) -> list[str]:
    parts: list[str] = []
    for para in _PARA_SPLIT.split(text):
        para = para.strip()
        if not para:
            continue
        if len(para) <= hard_limit:
            parts.append(para)
            continue
        for sent in re.split(r"(?<=[.!?])\s+|\n", para):
            sent = sent.strip()
            if not sent:
                continue
            if len(sent) <= hard_limit:
                parts.append(sent)
            else:
                for i in range(0, len(sent), hard_limit):
                    parts.append(sent[i:i + hard_limit])
    return parts


def chunk_text(
    text: str,
    chunk_size: int = 1500,
    overlap: int = 200,
    doc_id: str = "",
) -> list[dict]:
    """Split text into overlapping chunks with unique chunk IDs.

    chunk_id = MD5(doc_id + index + text) ensures chunks from different
    documents with identical boilerplate text still get distinct IDs.
    """
    paragraphs = _split_paragraphs(text, hard_limit=chunk_size)
    if not paragraphs:
        return []

    chunks: list[dict] = []
    buffer = ""
    chunk_index = 0

    def flush(buf: str) -> None:
        nonlocal chunk_index
        key = f"{doc_id}\x00{chunk_index}\x00{buf}"
        h = hashlib.md5(key.encode()).hexdigest()
        chunks.append({"chunk_id": h, "chunk_index": chunk_index, "text": buf})
        chunk_index += 1

    for para in paragraphs:
        if not buffer:
            buffer = para
            continue
        if len(buffer) + 2 + len(para) <= chunk_size:
            buffer = f"{buffer}\n\n{para}"
            continue
        flush(buffer)
        if overlap > 0 and len(buffer) > overlap and len(para) + 2 + overlap <= chunk_size:
            tail = buffer[-overlap:]
            buffer = f"{tail}\n\n{para}"
        else:
            buffer = para

    if buffer:
        flush(buffer)

    return chunks
