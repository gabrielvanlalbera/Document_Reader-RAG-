"""Small retrieval evaluation helpers."""
from __future__ import annotations


def recall_at_k(retrieved_sources: list[str], relevant_sources: set[str], k: int = 5) -> float:
    if not relevant_sources:
        return 0.0
    found = set(retrieved_sources[:k]) & relevant_sources
    return len(found) / len(relevant_sources)


def reciprocal_rank(retrieved_sources: list[str], relevant_sources: set[str]) -> float:
    for rank, source in enumerate(retrieved_sources, start=1):
        if source in relevant_sources:
            return 1.0 / rank
    return 0.0
