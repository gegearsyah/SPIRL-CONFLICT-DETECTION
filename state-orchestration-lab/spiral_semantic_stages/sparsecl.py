"""
SparseCL reranker — Stage 1.5 (matches Spiral `backend/app/services/sparsecl_service.py`).
"""

from __future__ import annotations

import logging
import math
from typing import Any

import numpy as np

from .settings import SpiralSemanticSettings, get_settings

log = logging.getLogger("spiral_semantic_stages.sparsecl")

_model = None
_model_name_loaded: str | None = None
_model_load_attempted = False


def _get_model(cfg: SpiralSemanticSettings):
    global _model, _model_name_loaded, _model_load_attempted

    want = cfg.sparsecl_model
    if _model is not None and _model_name_loaded == want:
        return _model
    if _model is None and _model_load_attempted and _model_name_loaded == want:
        return None

    if _model_name_loaded is not None and _model_name_loaded != want:
        _model = None
        _model_load_attempted = False

    _model_load_attempted = True
    _model_name_loaded = want
    try:
        from sentence_transformers import SentenceTransformer

        log.info("Loading SparseCL model: %s", want)
        _model = SentenceTransformer(want)
        log.info("SparseCL model loaded successfully")
        return _model
    except Exception as exc:
        log.warning("SparseCL model unavailable: %s", exc)
        _model = None
        return None


def reset_sparsecl_cache_for_tests() -> None:
    global _model, _model_name_loaded, _model_load_attempted
    _model = None
    _model_name_loaded = None
    _model_load_attempted = False


def sparsecl_available(settings: SpiralSemanticSettings | None = None) -> bool:
    cfg = settings or get_settings()
    return _get_model(cfg) is not None


def hoyer_sparsity(diff: np.ndarray) -> float:
    n = len(diff)
    if n <= 1:
        return 0.0

    l1 = float(np.sum(np.abs(diff)))
    l2 = float(np.sqrt(np.sum(diff**2)))

    if l2 == 0:
        return 0.0

    sqrt_n = math.sqrt(n)
    denom = sqrt_n - 1.0
    if denom == 0:
        return 0.0

    return (sqrt_n - l1 / l2) / denom


def rerank_candidates(
    query_text: str,
    candidates: list[dict[str, Any]],
    *,
    settings: SpiralSemanticSettings | None = None,
    alpha: float | None = None,
) -> list[dict[str, Any]]:
    cfg = settings or get_settings()
    model = _get_model(cfg)
    if model is None:
        return candidates

    if alpha is None:
        alpha = cfg.sparsecl_alpha

    bodies = [c.get("body") or "" for c in candidates]
    valid_indices = [i for i, b in enumerate(bodies) if b.strip()]

    if not valid_indices:
        return candidates

    try:
        texts_to_encode = [query_text] + [bodies[i] for i in valid_indices]
        embeddings = model.encode(texts_to_encode, normalize_embeddings=True)

        query_emb = np.array(embeddings[0], dtype=np.float64)

        for rank, vi in enumerate(valid_indices):
            cand_emb = np.array(embeddings[rank + 1], dtype=np.float64)
            cos = float(np.dot(query_emb, cand_emb))
            diff = query_emb - cand_emb
            hoy = hoyer_sparsity(diff)
            combined = cos + alpha * hoy

            candidates[vi]["sparsecl_cosine"] = round(cos, 4)
            candidates[vi]["sparsecl_hoyer"] = round(hoy, 4)
            candidates[vi]["sparsecl_combined"] = round(combined, 4)

        candidates.sort(
            key=lambda c: c.get("sparsecl_combined", -1),
            reverse=True,
        )

        return candidates
    except Exception as exc:
        log.warning("SparseCL reranking failed: %s", exc)
        return candidates
