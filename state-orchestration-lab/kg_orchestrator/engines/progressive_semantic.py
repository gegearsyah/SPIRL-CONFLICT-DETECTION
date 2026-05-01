"""Paper §3.2 axis 2: Spiral-aligned progressive semantic pipeline on cohort neighbors."""

from __future__ import annotations

from kg_orchestrator.models import (
    FactProposal,
    GovernanceFinding,
    GraphContext,
    Severity,
)


def progressive_semantic_stack_available() -> bool:
    """True if spiral_semantic_stages + NLI can be loaded (SparseCL remains optional)."""
    try:
        from spiral_semantic_stages.nli import nli_available

        return bool(nli_available())
    except ImportError:
        return False


class ProgressiveSemanticContradictionEngine:
    """Cosine → SparseCL/E-Verify → predicate gate → bidirectional margin NLI."""

    name = "semantic"

    def evaluate(
        self, proposal: FactProposal, ctx: GraphContext
    ) -> list[GovernanceFinding]:
        try:
            from spiral_semantic_stages import (
                candidates_from_neighbors,
                check_semantic_contradictions_stages,
                get_settings,
            )
        except ImportError:
            return []

        if proposal.embedding is None:
            return []

        cfg = get_settings()
        thr = cfg.conflict_embedding_similarity_threshold
        # Experiment C replay: cohort neighbors are gold paired contradictors; cosine can
        # sit below production τ_low when keys drift — still run progressive stages.
        if proposal.metadata.get(
            "paper3_relax_stage1_for_semantic_replay"
        ) or proposal.metadata.get("governance_replay_relax_stage1_semantic"):
            thr = 0.0
        cands = candidates_from_neighbors(
            proposal,
            ctx.neighbor_facts,
            similarity_threshold=thr,
            limit=10,
        )
        if not cands:
            return []

        raw = check_semantic_contradictions_stages(
            proposal.key,
            proposal.body,
            cands,
            settings=cfg,
            limit=10,
            proposed_kind=None,
        )

        out: list[GovernanceFinding] = []
        for h in raw:
            ct = str(h.get("conflict_type") or "")
            if ct == "semantic_contradiction":
                sev_raw = str(h.get("severity") or "high").lower()
                sev = Severity.high if sev_raw == "high" else Severity.warning
                out.append(
                    GovernanceFinding(
                        engine=self.name,
                        conflict_class="semantic_contradiction",
                        severity=sev,
                        message=h.get("summary")
                        or "Progressive semantic pipeline: contradiction",
                        details=dict(h.get("details") or {}),
                    )
                )
            elif ct == "unverified_similarity":
                out.append(
                    GovernanceFinding(
                        engine=self.name,
                        conflict_class="unverified_similarity",
                        severity=Severity.info,
                        message=h.get("summary") or "High similarity; NLI inconclusive",
                        details=dict(h.get("details") or {}),
                    )
                )
        return out
