"""
Replica of Spiral's **semantic contradiction** stages for research (state-orchestration-lab).

Does not replace `kg_orchestrator/engines/semantic.py` (paper baselines). Use this package
when you want parity with Spiral `semantic_checker.py` + **Spiral/docs/CONFLICT_DETECTION_ARCHITECTURE.md**
(predicate overlap, bidirectional margin-gated NLI, SparseCL + E-Verify) on pre-retrieved neighbors.
"""

from .neighbors import candidates_from_neighbors
from .nli import classify_pair_probs
from .pipeline import check_semantic_contradictions_stages
from .settings import SpiralSemanticSettings, get_settings, reload_settings

__all__ = [
    "SpiralSemanticSettings",
    "candidates_from_neighbors",
    "check_semantic_contradictions_stages",
    "classify_pair_probs",
    "get_settings",
    "reload_settings",
]
