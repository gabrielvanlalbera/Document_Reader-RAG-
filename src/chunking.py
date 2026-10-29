"""Chunk records while retaining source metadata."""
from __future__ import annotations
import re


def split_text(text: str, chunk_size: int = 1000, overlap: int = 150) -> list[str]:
    if chunk_size < 1:
        raise ValueError("chunk_size must be positive")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be non-negative and smaller than chunk_size")
    normalized = re.sub(r"\s+", " ", text).strip()
    if not normalized:
        return []
    chunks = []
    start = 0
    while start < len(normalized):
        end = min(start + chunk_size, len(normalized))
        if end < len(normalized):
            boundary = normalized.rfind(" ", start + int(chunk_size * 0.65), end)
            if boundary > start:
                end = boundary
        piece = normalized[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= len(normalized):
            break
        start = max(end - overlap, start + 1)
    return chunks


def build_chunks(records: list[dict], chunk_size: int = 1000, overlap: int = 150) -> list[dict]:
    chunks = []
    for record in records:
        for local_index, text in enumerate(split_text(record["text"], chunk_size, overlap), start=1):
            chunks.append({
                "id": f"doc{len(chunks)+1}",
                "text": text,
                "source": record["source"],
                "location": record.get("location", "unknown"),
                "chunk_in_record": local_index,
            })
    return chunks
