"""Environment-driven settings aligned with Spiral `backend/app/core/config.py` (semantic slice only)."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class SpiralSemanticSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    conflict_embedding_similarity_threshold: float = Field(
        default=0.35,
        description="Stage 1: min cosine on pre-retrieved neighbors (legacy CONFLICT_EMBEDDING_SIMILARITY_THRESHOLD; Spiral hybrid uses lower dense floor in DB)",
    )
    contradiction_high_severity_similarity: float = Field(
        default=0.80,
        description="When NLI unavailable: unverified_similarity floor",
    )
    nli_contradiction_confidence_threshold: float = Field(
        default=0.80,
        description="Stage 2: min min(forward, reverse) p(contradiction) after gates",
    )
    nli_contradiction_margin_threshold: float = Field(
        default=0.40,
        description="Stage 2: forward contradiction_prob - max(entailment, neutral) must exceed this",
    )
    nli_contradiction_reverse_margin_threshold: float = Field(
        default=0.25,
        description="Stage 2: reverse margin floor when forward is strong (0 disables asymmetric path)",
    )
    nli_forward_strong_confidence: float = Field(
        default=0.95,
        description="Relax reverse margin when forward contradiction confidence ≥ this",
    )
    nli_forward_strong_margin: float = Field(
        default=0.60,
        description="Relax reverse margin when forward NLI margin ≥ this",
    )
    nli_bidirectional_enabled: bool = Field(
        default=True,
        description="Stage 2: require NLI contradiction in both A→B and B→A",
    )
    nli_forward_dominant_override_enabled: bool = Field(
        default=False,
        description="If true, emit on overwhelming forward NLI even when reverse is not contradiction",
    )
    nli_forward_dominant_min_confidence: float = Field(default=0.97)
    nli_forward_dominant_min_margin: float = Field(default=0.80)
    nli_predicate_overlap_threshold: float = Field(
        default=0.15,
        description="Stage 1.75: min Jaccard on content words; 0 disables",
    )
    nli_predicate_overlap_mode: str = Field(
        default="soft",
        description="soft = recall-safe rescue (Spiral Apr 2026); hard = strict Jaccard veto",
    )
    semantic_overlap_no_rescue_floor: float = Field(
        default=0.08,
        description="Below this Jaccard, similarity/Hoyer alone cannot rescue in soft mode",
    )
    nli_predicate_overlap_rescue_similarity: float = Field(default=0.90)
    nli_predicate_overlap_rescue_hoyer: float = Field(default=0.30)
    nli_model_name: str = Field(default="cross-encoder/nli-deberta-v3-base")
    sparsecl_model: str = Field(default="SparseCL/BGE-SparseCL-arguana")
    sparsecl_alpha: float = Field(default=1.0)
    sparsity_entailment_floor: float = Field(
        default=0.32,
        description="E-Verify: Hoyer below this skips NLI (Spiral Apr 2026 default)",
    )
    sparsecl_everify_enabled: bool = Field(
        default=False,
        description="E-Verify Hoyer pre-filter; Spiral Apr 2026 preset false (rerank only)",
    )


@lru_cache
def get_settings() -> SpiralSemanticSettings:
    return SpiralSemanticSettings()


def reload_settings() -> SpiralSemanticSettings:
    get_settings.cache_clear()
    return get_settings()
