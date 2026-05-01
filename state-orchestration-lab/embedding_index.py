#!/usr/bin/env python3
"""
Local embedding index for the ablation harness.

Pre-computes sentence-transformer embeddings for all baseline facts,
caches to .npz on disk, and provides cosine-similarity retrieval.
Replaces Neo4j/pgvector vector search for offline evaluation.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import numpy as np

log = logging.getLogger("ablation.embedding_index")

_LAB_DIR = Path(__file__).resolve().parent
_CACHE_DIR = _LAB_DIR / ".embedding_cache"

_BI_ENCODER_MODEL = os.environ.get(
    "ABLATION_EMBEDDING_MODEL",
    "all-MiniLM-L6-v2",
)


class EmbeddingIndex:
    """Pre-computed embedding index with cosine-similarity retrieval."""

    def __init__(
        self,
        facts: list[dict[str, Any]],
        *,
        model_name: str | None = None,
        cache_dir: Path | None = None,
    ) -> None:
        self._facts = facts
        self._model_name = model_name or _BI_ENCODER_MODEL
        self._cache_dir = cache_dir or _CACHE_DIR
        self._embeddings: np.ndarray | None = None
        self._model = None

    @property
    def model_name(self) -> str:
        return self._model_name

    def _get_model(self):
        if self._model is not None:
            return self._model
        from sentence_transformers import SentenceTransformer

        log.info("Loading bi-encoder: %s", self._model_name)
        self._model = SentenceTransformer(self._model_name)
        return self._model

    def _cache_path(self) -> Path:
        safe_name = self._model_name.replace("/", "_").replace("\\", "_")
        return self._cache_dir / f"facts_{safe_name}_{len(self._facts)}.npz"

    def build_or_load(self, *, force: bool = False) -> None:
        """Compute or load cached embeddings for all baseline facts."""
        cache = self._cache_path()
        if not force and cache.is_file():
            data = np.load(cache)
            self._embeddings = data["embeddings"]
            log.info("Loaded cached embeddings: %s (%d facts)", cache.name, len(self._embeddings))
            if len(self._embeddings) != len(self._facts):
                log.warning(
                    "Cache size mismatch (%d vs %d), recomputing",
                    len(self._embeddings),
                    len(self._facts),
                )
                self._embeddings = None

        if self._embeddings is not None:
            return

        model = self._get_model()
        texts = [f.get("body", "") for f in self._facts]
        log.info("Computing embeddings for %d facts with %s", len(texts), self._model_name)
        embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=True)
        self._embeddings = np.array(embeddings, dtype=np.float32)

        self._cache_dir.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(cache, embeddings=self._embeddings)
        log.info("Cached embeddings to %s", cache)

    def embed_text(self, text: str) -> np.ndarray:
        """Embed a single text (for query embedding)."""
        model = self._get_model()
        emb = model.encode([text], normalize_embeddings=True)
        return np.array(emb[0], dtype=np.float32)

    def retrieve_neighbors(
        self,
        query_text: str,
        *,
        top_k: int = 10,
        threshold: float = 0.0,
        exclude_keys: set[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Find the most similar baseline facts to a query text."""
        if self._embeddings is None:
            raise RuntimeError("Call build_or_load() before retrieving neighbors")

        query_emb = self.embed_text(query_text)
        # Cosine similarity (embeddings are already normalized)
        sims = self._embeddings @ query_emb

        exclude = exclude_keys or set()
        candidates: list[tuple[float, int]] = []
        for idx, sim in enumerate(sims):
            if float(sim) < threshold:
                continue
            fact_key = self._facts[idx].get("key", "")
            if fact_key in exclude:
                continue
            candidates.append((float(sim), idx))

        # Sort by similarity descending, take top_k
        candidates.sort(key=lambda x: x[0], reverse=True)
        candidates = candidates[:top_k]

        results: list[dict[str, Any]] = []
        for sim_score, idx in candidates:
            fact = self._facts[idx]
            results.append({
                "key": fact.get("key", ""),
                "body": fact.get("body", ""),
                "kind": fact.get("kind"),
                "id": f"baseline-{idx}",
                "similarity": round(sim_score, 6),
            })
        return results
