#!/usr/bin/env python3
"""
Step 2: load graph slice from Neo4j for one epistemic key, run all governance engines.

Usage:
  python run_aura_governance.py --key stack.secrets
  python run_aura_governance.py --key research.p3.sem.3.queue --bounds max_replicas:10

Loads .env from this folder.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parent
load_dotenv(_ROOT / ".env", override=False)
load_dotenv(_ROOT / "spiral_semantic_stages" / ".env", override=False)


def parse_bounds(s: str | None) -> dict[str, float]:
    if not s:
        return {}
    out: dict[str, float] = {}
    for part in s.split(","):
        part = part.strip()
        if not part:
            continue
        if ":" not in part:
            raise ValueError(f"Bad bound {part!r}, use name:float")
        k, v = part.split(":", 1)
        out[k.strip()] = float(v.strip())
    return out


def main() -> int:
    p = argparse.ArgumentParser(description="Run governance engines against Neo4j context")
    p.add_argument("--key", required=True, help="Epistemic key to match in Neo4j")
    p.add_argument(
        "--bounds",
        default="",
        help="Optional constraint bounds, e.g. max_replicas:10,team_cap:5",
    )
    p.add_argument(
        "--body",
        default="",
        help="Proposal body text (default: empty; temporal/dependency still run from DB)",
    )
    args = p.parse_args()

    try:
        from datetime import datetime, timezone

        from kg_orchestrator import FactProposal, GovernanceOrchestrator
        from kg_orchestrator.engines import (
            DependencyImpactEngine,
            OntologyConstraintEngine,
            SemanticContradictionEngine,
            TemporalInvalidationEngine,
        )
        from kg_orchestrator.engines.progressive_semantic import (
            ProgressiveSemanticContradictionEngine,
            progressive_semantic_stack_available,
        )
        from kg_orchestrator.neo4j_io import Neo4jGraphAccessor
    except ImportError as e:
        print(e, file=sys.stderr)
        print("Run: pip install -r requirements.txt", file=sys.stderr)
        return 1

    bounds = parse_bounds(args.bounds) if args.bounds else {}

    try:
        acc = Neo4jGraphAccessor()
    except Exception as e:
        print(f"Neo4j connection failed: {e}", file=sys.stderr)
        return 1

    try:
        ctx = acc.load_context_for_key(args.key, constraint_bounds=bounds)
    finally:
        acc.close()

    print(f"Key: {args.key!r}")
    print(f"  same_key_facts in DB: {len(ctx.same_key_facts)}")
    print(f"  inbound dependency sources: {ctx.inbound_dependency_sources}")
    if not ctx.same_key_facts and not ctx.inbound_dependency_sources:
        print(
            "\nNo rows matched. Run: python run_neo4j_probe.py\n"
            "Then set NEO4J_FACT_LABEL / NEO4J_KEY_PROPERTY in .env to match your schema.",
            file=sys.stderr,
        )

    proposal = FactProposal(
        key=args.key,
        body=args.body or "(no proposal body supplied; use --body '...')",
        valid_from=datetime.now(timezone.utc),
        valid_until=None,
        embedding=None,
        metadata={},
    )

    sem = (
        ProgressiveSemanticContradictionEngine()
        if progressive_semantic_stack_available()
        else SemanticContradictionEngine()
    )
    orch = GovernanceOrchestrator(
        [
            TemporalInvalidationEngine(),
            sem,
            OntologyConstraintEngine(),
            DependencyImpactEngine(),
        ]
    )
    findings = asyncio.run(orch.evaluate_async(proposal, ctx))
    print(f"\nGovernance findings ({len(findings)}):")
    for f in findings:
        print(f"  [{f.engine}] {f.conflict_class} ({f.severity}): {f.message}")
    if not findings:
        print("  (none — expected if DB empty for this key and no deps/bounds)")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValueError as e:
        print(e, file=sys.stderr)
        raise SystemExit(1)
