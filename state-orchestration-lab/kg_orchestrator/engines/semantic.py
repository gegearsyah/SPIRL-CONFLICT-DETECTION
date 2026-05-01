"""Paper §3.2 axis 2: retrieval + NLI (hook for your embedding + cross-encoder service)."""

from __future__ import annotations

import math
from typing import Callable

from kg_orchestrator.models import (
    FactProposal,
    GovernanceFinding,
    GraphContext,
    Severity,
)

# Defaults from paper3 §3.2
TAU_LOW = 0.50
TAU_HIGH = 0.65


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


class SemanticContradictionEngine:
    name = "semantic"

    def __init__(
        self,
        nli_contradicts: Callable[[str, str], bool] | None = None,
        *,
        semantic_mode: str = "full",
    ) -> None:
        """
        nli_contradicts: given (proposal.body, neighbor.body) return True if contradiction.
        semantic_mode:
          - "full": high-sim bypass + NLI for tau_low <= sim < tau_high (paper §3.2).
          - "high_only": only sim >= tau_high (NLI ignored; ablation T+Sem_high).
          - "retrieval_strawman": flag contradiction for tau_low <= sim < tau_high without NLI
            (deliberately weak baseline to isolate NLI; not a deploy policy).
        """
        self._nli = nli_contradicts
        self._mode = semantic_mode

    def evaluate(
        self, proposal: FactProposal, ctx: GraphContext
    ) -> list[GovernanceFinding]:
        findings: list[GovernanceFinding] = []
        if proposal.embedding is None:
            return findings

        for nb in ctx.neighbor_facts:
            if nb.embedding is None:
                continue
            sim = _cosine(proposal.embedding, nb.embedding)
            if self._mode == "retrieval_strawman":
                if TAU_LOW <= sim < TAU_HIGH:
                    findings.append(
                        GovernanceFinding(
                            engine=self.name,
                            conflict_class="semantic_contradiction",
                            severity=Severity.high,
                            message="Retrieval-strawman: in-band cosine treated as contradiction",
                            details={"similarity": sim, "neighbor_key": nb.key},
                        )
                    )
                continue

            if sim >= TAU_HIGH:
                findings.append(
                    GovernanceFinding(
                        engine=self.name,
                        conflict_class="semantic_contradiction",
                        severity=Severity.high,
                        message="High cosine similarity bypass (structural warning)",
                        details={"similarity": sim, "neighbor_key": nb.key},
                    )
                )
                continue
            if sim < TAU_LOW:
                continue
            if self._mode == "high_only":
                continue
            nli = self._nli
            if nli is not None and nli(proposal.body, nb.body):
                findings.append(
                    GovernanceFinding(
                        engine=self.name,
                        conflict_class="semantic_contradiction",
                        severity=Severity.high,
                        message="NLI classified contradiction",
                        details={"similarity": sim, "neighbor_key": nb.key},
                    )
                )
        return findings
