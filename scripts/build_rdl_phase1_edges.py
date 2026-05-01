#!/usr/bin/env python3
"""
Emit real-data-lab/research/rdl_phase1_edges_plan.json — canonical SKF graph edges
for real_data_lab_phase1_mcp_run.py (implements / depends_on / related_to only).

Regenerate after corpus structure changes:
  python build_rdl_phase1_edges.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
BTC = _SCRIPTS.parent
OUT = BTC / "real-data-lab" / "research" / "rdl_phase1_edges_plan.json"


def build_edges() -> list[dict[str, str]]:
    edges: list[dict[str, str]] = []
    for i in range(1, 11):
        edges.append(
            {
                "source": f"f-feat-{i:02d}",
                "target": f"f-dec-{i:02d}",
                "edge_type": "implements",
                "justification": f"Feature {i:02d} implements paired architecture decision {i:02d}.",
            }
        )
    for i in range(1, 11):
        edges.append(
            {
                "source": f"f-dec-{i:02d}",
                "target": f"f-stack-{i:02d}",
                "edge_type": "depends_on",
                "justification": f"Decision {i:02d} assumes supporting stack component {i:02d}.",
            }
        )
    for i in range(1, 11):
        edges.append(
            {
                "source": f"f-con-{i:02d}",
                "target": f"f-dec-{i:02d}",
                "edge_type": "related_to",
                "justification": f"Constraint {i:02d} governs the same concern space as decision {i:02d}.",
            }
        )
    api_related: list[tuple[str, str, str]] = [
        ("f-api-02", "f-feat-04", "Search API integrates with search-backed feature."),
        ("f-api-03", "f-feat-01", "Catalog locations API registers catalog entities."),
        ("f-api-04", "f-feat-02", "Create/actions enumerates scaffolder/template actions."),
        ("f-api-05", "f-feat-07", "Metrics endpoint surfaces analytics instrumentation."),
        ("f-api-06", "f-feat-05", "RBAC permissions registry backs access control feature."),
        ("f-api-07", "f-feat-03", "TechDocs routing aligns with docs-like-code feature."),
        ("f-api-08", "f-dec-02", "Scaffolder task list ties to catalog entity model ADR."),
        ("f-api-09", "f-feat-07", "Analytics API matches portal telemetry feature."),
        ("f-api-10", "f-stack-01", "FetchApi relates to Node/Express backend stack."),
        ("f-api-11", "f-mig-06", "Task logs relate to batched migration operations."),
        ("f-api-12", "f-feat-06", "ChatOps migration list maps to batched migrations feature."),
        ("f-api-13", "f-feat-06", "ChatOps migration status maps to batched migrations feature."),
        ("f-api-14", "f-feat-01", "Identity API ties to catalog/entity context."),
        ("f-api-15", "f-feat-08", "Catalog entities by-query serves API-docs feature."),
    ]
    for src, tgt, jus in api_related:
        edges.append({"source": src, "target": tgt, "edge_type": "related_to", "justification": jus})
    for i in range(1, 7):
        edges.append(
            {
                "source": f"f-dep-{i:02d}",
                "target": f"f-stack-{i:02d}",
                "edge_type": "depends_on",
                "justification": f"Deployment pattern {i:02d} relies on stack tier {i:02d}.",
            }
        )
    for i in range(1, 8):
        edges.append(
            {
                "source": f"f-mig-{i:02d}",
                "target": f"f-dec-{i:02d}",
                "edge_type": "related_to",
                "justification": f"Migration {i:02d} operationalizes paired decision {i:02d}.",
            }
        )
    test_related: list[tuple[str, str, str]] = [
        ("f-test-01", "f-feat-02", "Scaffolder dry-run exercises template feature."),
        ("f-test-02", "f-dec-09", "GitLab DB testing validates batched migration decision."),
        ("f-test-03", "f-stack-02", "Jest suite targets React frontend stack."),
        ("f-test-04", "f-dec-09", "Migration CI checks align with batched migration ADR."),
        ("f-test-05", "f-feat-02", "TemplateExamples document scaffolder permutations."),
    ]
    for src, tgt, jus in test_related:
        edges.append({"source": src, "target": tgt, "edge_type": "related_to", "justification": jus})
    mon_related: list[tuple[str, str, str]] = [
        ("f-mon-01", "f-stack-09", "Catalog processing duration metric ties to Prometheus stack."),
        ("f-mon-02", "f-stack-09", "Queue delay metric ties to Prometheus stack."),
        ("f-mon-03", "f-api-05", "Scaffolder duration metric references metrics endpoint fact."),
        ("f-mon-04", "f-feat-06", "ChatOps migration telemetry maps to batched migrations feature."),
        ("f-mon-05", "f-dec-10", "Entity count metric relates to RBAC/catalog policy ADR."),
        ("f-mon-06", "f-stack-01", "Background task runs metric ties to Node backend stack."),
        ("f-mon-07", "f-feat-04", "Grafana alert integration relates to search feature surface."),
    ]
    for src, tgt, jus in mon_related:
        edges.append({"source": src, "target": tgt, "edge_type": "related_to", "justification": jus})
    return edges


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    edges = build_edges()
    OUT.write_text(json.dumps(edges, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(edges)} edges to {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
