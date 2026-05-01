"""Paper §3.2 axis 4: downstream dependency impact when indegree > 0."""

from __future__ import annotations

from kg_orchestrator.models import FactProposal, GovernanceFinding, GraphContext, Severity


class DependencyImpactEngine:
    name = "dependency"

    def __init__(
        self,
        *,
        min_inbound_sources: int = 1,
        use_multi_hop_count: bool = False,
    ) -> None:
        """
        min_inbound_sources: require at least this many direct inbound keys (prototype hook).
        use_multi_hop_count: if True and ctx.multi_hop_upstream_count is set, require it >= min_inbound_sources
        instead of len(inbound_dependency_sources) (richer structural signal when Neo4j fills the field).
        """
        self._min = max(1, min_inbound_sources)
        self._use_mh = use_multi_hop_count

    def evaluate(
        self, proposal: FactProposal, ctx: GraphContext
    ) -> list[GovernanceFinding]:
        if self._use_mh and ctx.multi_hop_upstream_count is not None:
            if ctx.multi_hop_upstream_count < self._min:
                return []
            n = ctx.multi_hop_upstream_count
        else:
            srcs = ctx.inbound_dependency_sources
            if len(srcs) < self._min:
                return []
            n = len(srcs)
        return [
            GovernanceFinding(
                engine=self.name,
                conflict_class="dependency_impact",
                severity=Severity.warning,
                message="Active inbound dependencies detected",
                details={
                    "sources": ctx.inbound_dependency_sources,
                    "count_used": n,
                    "min_required": self._min,
                },
            )
        ]
