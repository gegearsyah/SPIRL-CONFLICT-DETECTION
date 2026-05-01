"""Named ablation profiles for Paper 3 replay (governance engine composition)."""

from __future__ import annotations

import os
from typing import Callable

from kg_orchestrator.orchestrator import GovernanceOrchestrator
from kg_orchestrator.engines.dependency import DependencyImpactEngine
from kg_orchestrator.engines.ontology import OntologyConstraintEngine
from kg_orchestrator.engines.progressive_semantic import (
    ProgressiveSemanticContradictionEngine,
    progressive_semantic_stack_available,
)
from kg_orchestrator.engines.semantic import SemanticContradictionEngine
from kg_orchestrator.engines.temporal import TemporalInvalidationEngine

PROFILE_NAMES = (
    "T",
    "T_sem_high",
    "T_sem_retrieval",
    "T_sem_nli",
    "Full",
)


def _dependency_engine() -> DependencyImpactEngine:
    try:
        m = int(os.environ.get("DEPENDENCY_MIN_INBOUND", "1"))
    except ValueError:
        m = 1
    use_mh = os.environ.get("DEPENDENCY_USE_MULTIHOP", "").lower() in (
        "1",
        "true",
        "yes",
    )
    return DependencyImpactEngine(
        min_inbound_sources=max(1, m),
        use_multi_hop_count=use_mh,
    )


def _legacy_semantic_forced() -> bool:
    return os.environ.get("PAPER3_LEGACY_SEMANTIC", "").lower() in (
        "1",
        "true",
        "yes",
    )


def _semantic_axis_engine(
    nli_fn: Callable[[str, str], bool] | None,
) -> SemanticContradictionEngine | ProgressiveSemanticContradictionEngine:
    """
    Prefer Spiral progressive stack when installed (--nli-oracle / legacy env use
    SemanticContradictionEngine + nli_fn).
    """
    if _legacy_semantic_forced():
        if nli_fn is None:
            raise ValueError(
                "Legacy semantic requires an NLI callable (set PAPER3_LEGACY_SEMANTIC=0 "
                "to use progressive stack, or pass --nli-oracle with oracle NLI)"
            )
        return SemanticContradictionEngine(
            nli_contradicts=nli_fn,
            semantic_mode="full",
        )
    if progressive_semantic_stack_available():
        return ProgressiveSemanticContradictionEngine()
    if nli_fn is None:
        raise ValueError(
            "NLI unavailable: install requirements-eval.txt + requirements-spiral-stages.txt, "
            "or use --nli-oracle, or set PAPER3_LEGACY_SEMANTIC=1 with a cross-encoder."
        )
    return SemanticContradictionEngine(
        nli_contradicts=nli_fn,
        semantic_mode="full",
    )


def build_governance_orchestrator(
    profile: str,
    nli_fn: Callable[[str, str], bool] | None,
) -> GovernanceOrchestrator:
    """
    Build engine list for ablation ladder:
      T — temporal overlap only
      T_sem_high — temporal + cosine >= tau_high only
      T_sem_retrieval — temporal + retrieval strawman (in-band cosine => contradict)
      T_sem_nli — temporal + full semantic (progressive stack or legacy NLI)
      Full — temporal + semantic + ontology + dependency
    """
    p = profile.strip()
    if p not in PROFILE_NAMES:
        raise ValueError(f"Unknown profile {profile!r}; choose from {PROFILE_NAMES}")

    temporal = TemporalInvalidationEngine()
    ont = OntologyConstraintEngine()
    dep = _dependency_engine()

    if p == "T":
        return GovernanceOrchestrator([temporal])
    if p == "T_sem_high":
        return GovernanceOrchestrator(
            [temporal, SemanticContradictionEngine(semantic_mode="high_only")]
        )
    if p == "T_sem_retrieval":
        return GovernanceOrchestrator(
            [temporal, SemanticContradictionEngine(semantic_mode="retrieval_strawman")]
        )
    if p == "T_sem_nli":
        sem = _semantic_axis_engine(nli_fn)
        return GovernanceOrchestrator([temporal, sem])
    # Full
    sem = _semantic_axis_engine(nli_fn)
    return GovernanceOrchestrator([temporal, sem, ont, dep])
