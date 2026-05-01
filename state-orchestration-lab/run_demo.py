#!/usr/bin/env python3
"""Offline demo: four engines on synthetic GraphContext (no Neo4j required)."""

from datetime import datetime, timedelta

from kg_orchestrator import FactProposal, GovernanceOrchestrator
from kg_orchestrator.engines import (
    DependencyImpactEngine,
    OntologyConstraintEngine,
    SemanticContradictionEngine,
    TemporalInvalidationEngine,
)
from kg_orchestrator.models import ExistingFact, GraphContext


def main() -> None:
    now = datetime(2026, 4, 1, 12, 0, 0)
    proposal = FactProposal(
        key="svc.replicas",
        body="We run 99 replicas in production.",
        valid_from=now,
        valid_until=now + timedelta(days=30),
        embedding=[0.2, 0.8, 0.1],
        metadata={"proposed_rel_type": "USES_LEGACY"},
    )
    ctx = GraphContext(
        same_key_facts=[
            ExistingFact(
                key="svc.replicas",
                body="earlier",
                valid_from=now - timedelta(days=1),
                valid_until=now + timedelta(days=10),
                fact_id="f1",
            )
        ],
        neighbor_facts=[
            ExistingFact(
                key="svc.other",
                body="conflicting neighbor text",
                embedding=[0.19, 0.79, 0.11],
                fact_id="n1",
            )
        ],
        inbound_dependency_sources=["upstream.api"],
        constraint_bounds={"max_replicas": 10.0},
        allowed_rel_types={"USES", "IMPLEMENTS", "REFERENCES"},
    )

    orch = GovernanceOrchestrator(
        [
            TemporalInvalidationEngine(),
            SemanticContradictionEngine(),
            OntologyConstraintEngine(),
            DependencyImpactEngine(),
        ]
    )
    findings = orch.evaluate_sync(proposal, ctx)
    for f in findings:
        print(f"[{f.engine}] {f.conflict_class} ({f.severity}): {f.message}")


if __name__ == "__main__":
    main()
