"""Ontology / policy layer: numeric constraints (paper §3.2 axis 3) + optional type/rel rules.

Maps to 'constraint_violation' in paper3; extend with SHACL-like or OWL-style checks via GraphContext.
"""

from __future__ import annotations

import re

from kg_orchestrator.models import FactProposal, GovernanceFinding, GraphContext, Severity


_INT_RE = re.compile(r"\b(\d+)\b")


class OntologyConstraintEngine:
    name = "ontology"

    def evaluate(
        self, proposal: FactProposal, ctx: GraphContext
    ) -> list[GovernanceFinding]:
        findings: list[GovernanceFinding] = []
        # Axis 3 from paper: for each named bound v, extracted integers n must satisfy n <= 1.5 * v
        for name, cap in ctx.constraint_bounds.items():
            for n in (int(m.group(1)) for m in _INT_RE.finditer(proposal.body)):
                if n > 1.5 * cap:
                    findings.append(
                        GovernanceFinding(
                            engine=self.name,
                            conflict_class="constraint_violation",
                            severity=Severity.warning,
                            message=f"Integer {n} exceeds 1.5× bound {name}={cap}",
                            details={"bound_name": name, "bound_value": cap, "observed": n},
                        )
                    )

        # Optional: unknown edge types supplied by caller in metadata
        rel = proposal.metadata.get("proposed_rel_type")
        allowed = ctx.allowed_rel_types
        if rel and allowed is not None and rel not in allowed:
            findings.append(
                GovernanceFinding(
                    engine=self.name,
                    conflict_class="ontology_violation",
                    severity=Severity.warning,
                    message=f"Relationship type {rel!r} not in allowed set",
                    details={"proposed_rel_type": rel},
                )
            )
        return findings
