"""Paper §3.2 axis 1: same-key validity interval overlap."""

from __future__ import annotations

from datetime import datetime, timezone

from kg_orchestrator.models import (
    ExistingFact,
    FactProposal,
    GovernanceFinding,
    GraphContext,
    Severity,
)


def _utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _intervals_overlap(
    a0: datetime | None,
    a1: datetime | None,
    b0: datetime | None,
    b1: datetime | None,
) -> bool:
    """Open-ended intervals treated as unbounded on missing endpoints."""
    if a0 is None and a1 is None:
        return False
    if b0 is None and b1 is None:
        return False
    _past = datetime(1970, 1, 1, tzinfo=timezone.utc)
    _future = datetime(2100, 1, 1, tzinfo=timezone.utc)
    sn = _utc(a0) or _past
    en = _utc(a1) or _future
    so = _utc(b0) or _past
    eo = _utc(b1) or _future
    return sn < eo and so < en


class TemporalInvalidationEngine:
    name = "temporal"

    def evaluate(
        self, proposal: FactProposal, ctx: GraphContext
    ) -> list[GovernanceFinding]:
        findings: list[GovernanceFinding] = []
        for other in ctx.same_key_facts:
            if _intervals_overlap(
                proposal.valid_from,
                proposal.valid_until,
                other.valid_from,
                other.valid_until,
            ):
                findings.append(
                    GovernanceFinding(
                        engine=self.name,
                        conflict_class="temporal_invalidation",
                        severity=Severity.warning,
                        message=f"Validity overlap on key {proposal.key!r}",
                        details={"other_fact_id": other.fact_id},
                    )
                )
        return findings
