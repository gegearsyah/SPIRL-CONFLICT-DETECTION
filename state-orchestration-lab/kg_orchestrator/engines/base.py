from __future__ import annotations

from typing import Protocol

from kg_orchestrator.models import FactProposal, GovernanceFinding, GraphContext


class GovernanceEngine(Protocol):
    name: str

    def evaluate(
        self, proposal: FactProposal, ctx: GraphContext
    ) -> list[GovernanceFinding]:
        ...
