"""Helpers to build Stage-1 candidate dicts from lab `GraphContext` / `ExistingFact`."""

from __future__ import annotations

import math
from typing import Any

from kg_orchestrator.models import ExistingFact, FactProposal


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def candidates_from_neighbors(
    proposal: FactProposal,
    neighbors: list[ExistingFact],
    *,
    similarity_threshold: float,
    limit: int,
) -> list[dict[str, Any]]:
    """
    Mirror Spiral Stage 1 *after* vector search: same-key excluded, sim >= threshold,
    sorted by similarity descending, capped at `limit`.

    Each dict has: key, body, similarity, id (from fact_id), kind (optional, absent).
    """
    if proposal.embedding is None:
        return []

    out: list[dict[str, Any]] = []
    for nb in neighbors:
        if nb.key == proposal.key:
            continue
        if nb.embedding is None:
            continue
        sim = _cosine(proposal.embedding, nb.embedding)
        if sim < similarity_threshold:
            continue
        out.append(
            {
                "key": nb.key,
                "body": nb.body,
                "similarity": sim,
                "id": nb.fact_id,
            }
        )

    out.sort(key=lambda c: float(c.get("similarity") or 0), reverse=True)
    return out[:limit]
