#!/usr/bin/env python3
"""
Ablation configuration grid for the semantic contradiction pipeline sweep.

Each config corresponds to one column in the ablation table, progressively
adding defenses (A→E base model, F→G multi-dataset model).

Aligned with Spiral/docs/CONFLICT_DETECTION_ARCHITECTURE.md (Apr 2026):
E-Verify (Hoyer pre-filter) is off by default; SparseCL rerank still runs when installed.
Config G uses asymmetric reverse margin (0.25 when forward NLI is strong), not a lowered forward margin.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class AblationConfig:
    """One pipeline configuration for the ablation sweep."""

    name: str
    description: str

    # NLI model
    nli_model_name: str = "cross-encoder/nli-deberta-v3-base"

    # Stage 2: NLI gates
    nli_bidirectional_enabled: bool = True
    nli_contradiction_confidence_threshold: float = 0.80
    nli_contradiction_margin_threshold: float = 0.40
    # 0 = symmetric reverse (always same floor as forward margin); >0 enables asymmetric relax when forward is strong
    nli_contradiction_reverse_margin_threshold: float = 0.0

    # Stage 1: embedding retrieval (cosine on index neighbors; matches Spiral legacy reporting default)
    conflict_embedding_similarity_threshold: float = 0.35

    # Stage 1.5: SparseCL E-Verify (Hoyer pre-filter); rerank runs whenever SparseCL is available
    sparsecl_everify_enabled: bool = False

    # Stage 1.75: predicate overlap gate
    nli_predicate_overlap_threshold: float = 0.0  # 0 = disabled
    nli_predicate_overlap_mode: str = "soft"

    def to_settings_overrides(self) -> dict[str, Any]:
        """Return a dict of overrides for SpiralSemanticSettings fields."""
        return {
            "nli_model_name": self.nli_model_name,
            "nli_bidirectional_enabled": self.nli_bidirectional_enabled,
            "nli_contradiction_confidence_threshold": self.nli_contradiction_confidence_threshold,
            "nli_contradiction_margin_threshold": self.nli_contradiction_margin_threshold,
            "nli_contradiction_reverse_margin_threshold": self.nli_contradiction_reverse_margin_threshold,
            "conflict_embedding_similarity_threshold": self.conflict_embedding_similarity_threshold,
            "sparsecl_everify_enabled": self.sparsecl_everify_enabled,
            "nli_predicate_overlap_threshold": self.nli_predicate_overlap_threshold,
            "nli_predicate_overlap_mode": self.nli_predicate_overlap_mode,
        }

    def short_label(self) -> str:
        """Short label for LaTeX table column."""
        return self.name.split("_", 1)[0]


# ── Configuration Grid ───────────────────────────────────────────────────────

ABLATION_CONFIGS: list[AblationConfig] = [
    AblationConfig(
        name="A_base_unidirectional",
        description="Base model, unidirectional NLI, no margin, no SparseCL E-Verify, no predicate gate",
        nli_model_name="cross-encoder/nli-deberta-v3-base",
        nli_bidirectional_enabled=False,
        nli_contradiction_margin_threshold=0.0,
        nli_contradiction_reverse_margin_threshold=0.0,
        sparsecl_everify_enabled=False,
        nli_predicate_overlap_threshold=0.0,
    ),
    AblationConfig(
        name="B_base_bidirectional",
        description="Base model, bidirectional NLI, no margin, no SparseCL E-Verify, no predicate gate",
        nli_model_name="cross-encoder/nli-deberta-v3-base",
        nli_bidirectional_enabled=True,
        nli_contradiction_margin_threshold=0.0,
        nli_contradiction_reverse_margin_threshold=0.0,
        sparsecl_everify_enabled=False,
        nli_predicate_overlap_threshold=0.0,
    ),
    AblationConfig(
        name="C_base_margin",
        description="Base model, bidirectional + margin 0.40 (symmetric), no E-Verify, no predicate gate",
        nli_model_name="cross-encoder/nli-deberta-v3-base",
        nli_bidirectional_enabled=True,
        nli_contradiction_margin_threshold=0.40,
        nli_contradiction_reverse_margin_threshold=0.0,
        sparsecl_everify_enabled=False,
        nli_predicate_overlap_threshold=0.0,
    ),
    AblationConfig(
        name="D_base_predicate",
        description="Base model, bidirectional + margin + soft predicate gate (0.15), no E-Verify",
        nli_model_name="cross-encoder/nli-deberta-v3-base",
        nli_bidirectional_enabled=True,
        nli_contradiction_margin_threshold=0.40,
        nli_contradiction_reverse_margin_threshold=0.0,
        sparsecl_everify_enabled=False,
        nli_predicate_overlap_threshold=0.15,
        nli_predicate_overlap_mode="soft",
    ),
    AblationConfig(
        name="E_base_full",
        description="Base model: bidirectional + margin + soft predicate + SparseCL rerank (E-Verify off, Apr 2026 preset)",
        nli_model_name="cross-encoder/nli-deberta-v3-base",
        nli_bidirectional_enabled=True,
        nli_contradiction_margin_threshold=0.40,
        nli_contradiction_reverse_margin_threshold=0.0,
        sparsecl_everify_enabled=False,
        nli_predicate_overlap_threshold=0.15,
        nli_predicate_overlap_mode="soft",
    ),
    AblationConfig(
        name="F_wanli_full",
        description="WANLI-tuned DeBERTa-v3-large + same stack as E (rerank, no E-Verify)",
        nli_model_name="MoritzLaurer/DeBERTa-v3-large-mnli-fever-anli-ling-wanli",
        nli_bidirectional_enabled=True,
        nli_contradiction_margin_threshold=0.40,
        nli_contradiction_reverse_margin_threshold=0.0,
        sparsecl_everify_enabled=False,
        nli_predicate_overlap_threshold=0.15,
        nli_predicate_overlap_mode="soft",
    ),
    AblationConfig(
        name="G_wanli_relaxed",
        description="WANLI model + asymmetric reverse margin 0.25 when forward NLI is strong (forward margin stays 0.40)",
        nli_model_name="MoritzLaurer/DeBERTa-v3-large-mnli-fever-anli-ling-wanli",
        nli_bidirectional_enabled=True,
        nli_contradiction_margin_threshold=0.40,
        nli_contradiction_reverse_margin_threshold=0.25,
        sparsecl_everify_enabled=False,
        nli_predicate_overlap_threshold=0.15,
        nli_predicate_overlap_mode="soft",
    ),
]

CONFIG_BY_NAME: dict[str, AblationConfig] = {c.name: c for c in ABLATION_CONFIGS}


def get_configs(names: list[str] | None = None) -> list[AblationConfig]:
    """Return configs by name, or all if names is None."""
    if names is None:
        return list(ABLATION_CONFIGS)
    result = []
    for n in names:
        if n not in CONFIG_BY_NAME:
            raise ValueError(f"Unknown config: {n}. Available: {list(CONFIG_BY_NAME.keys())}")
        result.append(CONFIG_BY_NAME[n])
    return result
