"""
Offline hybrid re-split cascade (Spiral `cascade_router` v2.0 shape).

Runs Stages 1→5 in strict cost order, maintains deterministic temporal prune_set,
merges structural planes (temporal nonterminal + structured constraint + dependency
+ semantic constraint), runs Stage 5 progressive semantic pipeline on pre-retrieved
neighbors, then applies the same arbitration + signal contract as production.

Stage 5 here uses `spiral_semantic_stages` (NLI-primary / progressive stack) without
calling OpenRouter — mirroring live behavior when the LLM judge is unavailable or
when evaluating the local verifier slice only.
"""

from __future__ import annotations

import time
from typing import Any

from kg_orchestrator.cascade_arbitration import (
    _SIGNAL_CONTRACT_VERSION,
    apply_signal_contract,
    arbitrate_planes,
    conflict_pair_key,
    deduplicate_cascade_conflicts,
    split_temporal_conflicts,
    standardize_stage_trace,
    update_prune_set,
)
from kg_orchestrator.engines.dependency import DependencyImpactEngine
from kg_orchestrator.engines.ontology import OntologyConstraintEngine
from kg_orchestrator.engines.temporal import TemporalInvalidationEngine
from kg_orchestrator.models import (
    ExistingFact,
    FactProposal,
    GovernanceFinding,
    GraphContext,
)


def _norm_body(s: str) -> str:
    return " ".join(s.split()).strip().lower()


def _governance_to_cascade(
    g: GovernanceFinding,
    *,
    proposal_key: str,
    conflicting_fact_key: str | None = None,
    conflicting_fact_id: str | None = None,
) -> dict[str, Any]:
    details = dict(g.details or {})
    details.setdefault("proposed_key", proposal_key)
    return {
        "conflict_type": g.conflict_class,
        "severity": g.severity.value if hasattr(g.severity, "value") else str(g.severity),
        "message": g.message,
        "conflicting_fact_key": conflicting_fact_key,
        "conflicting_fact_id": conflicting_fact_id,
        "details": details,
    }


def _findings_temporal_to_cascade(
    findings: list[GovernanceFinding], proposal_key: str, ctx: GraphContext
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    other_by_id = {f.fact_id or f.key: f for f in ctx.same_key_facts}
    for g in findings:
        if g.conflict_class != "temporal_invalidation":
            continue
        oid = g.details.get("other_fact_id")
        other = other_by_id.get(oid)
        nk = other.key if other else str(oid or "")
        c = _governance_to_cascade(
            g,
            proposal_key=proposal_key,
            conflicting_fact_key=nk,
            conflicting_fact_id=str(oid) if oid else None,
        )
        c["details"]["detection_method"] = "temporal_lane_interval_overlap"
        c["details"]["temporal_case"] = "interval_overlap"
        out.append(c)
    return out


def _findings_constraints_to_cascade(
    findings: list[GovernanceFinding], proposal_key: str
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for g in findings:
        if g.conflict_class != "constraint_violation":
            continue
        d = dict(g.details or {})
        d.setdefault("lane_source", "constraint_structured")
        d.setdefault("constraint_type", d.get("constraint_type") or "numeric_bounds")
        d.setdefault("constraint_label", d.get("bound_name") or "numeric_cap")
        gg = GovernanceFinding(
            engine=g.engine,
            conflict_class=g.conflict_class,
            severity=g.severity,
            message=g.message,
            details=d,
        )
        out.append(
            _governance_to_cascade(
                gg,
                proposal_key=proposal_key,
                conflicting_fact_key=None,
            )
        )
    return out


def _findings_dependency_to_cascade(
    findings: list[GovernanceFinding], proposal_key: str
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for g in findings:
        if g.conflict_class != "dependency_impact":
            continue
        d = dict(g.details or {})
        srcs = list(d.get("sources") or [])
        d["edge_type"] = "DEPENDS_ON"
        d["edge_path"] = srcs[:8] or [proposal_key]
        d.setdefault("traversal_depth", 1)
        gg = GovernanceFinding(
            engine=g.engine,
            conflict_class=g.conflict_class,
            severity=g.severity,
            message=g.message,
            details=d,
        )
        anchor = srcs[0] if srcs else proposal_key
        out.append(
            _governance_to_cascade(
                gg,
                proposal_key=proposal_key,
                conflicting_fact_key=str(anchor),
            )
        )
    return out


def _precascade_same_key_body_diff(
    proposal_key: str, proposal_body: str, ctx: GraphContext
) -> list[dict[str, Any]]:
    conflicts: list[dict[str, Any]] = []
    for other in ctx.same_key_facts:
        if _norm_body(other.body) != _norm_body(proposal_body):
            conflicts.append(
                {
                    "conflict_type": "contradiction",
                    "severity": "high",
                    "message": "Same-key body rewrite",
                    "conflicting_fact_key": other.key,
                    "conflicting_fact_id": other.fact_id,
                    "details": {
                        "proposed_key": proposal_key,
                        "lane_source": "precascade",
                        "detection_method": "same_key_body_diff",
                    },
                }
            )
    return deduplicate_cascade_conflicts(conflicts)


def build_graph_context_for_key(
    proposal_key: str,
    proposal_body: str,
    baseline_rows: list[dict[str, Any]],
) -> GraphContext:
    same_key: list[ExistingFact] = []
    for row in baseline_rows:
        if row.get("key") != proposal_key:
            continue
        same_key.append(
            ExistingFact(
                key=row["key"],
                body=row.get("body") or row.get("value") or "",
                valid_from=None,
                valid_until=None,
                fact_id=row.get("key"),
            )
        )
    return GraphContext(same_key_facts=same_key, neighbor_facts=[])


def run_cascade_lab(
    *,
    proposal_key: str,
    proposal_body: str,
    proposal_embedding: list[float] | None,
    baseline_rows: list[dict[str, Any]],
    neighbor_dicts: list[dict[str, Any]],
    semantic_settings: Any,
    graph_ctx: GraphContext | None = None,
    execution_context: str = "preflight",
    conflict_execution_profile: str | None = "research",
) -> dict[str, Any]:
    """
    Returns the same top-level keys as Spiral `run_cascade` when include_trace=True,
    minus DB-backed stage internals.
    """
    t0 = time.monotonic()
    ctx = graph_ctx or build_graph_context_for_key(proposal_key, proposal_body, baseline_rows)
    fact: dict[str, Any] = {
        "key": proposal_key,
        "body": proposal_body,
        "id": proposal_key,
        "kind": None,
    }

    proposal = FactProposal(
        key=proposal_key,
        body=proposal_body,
        embedding=proposal_embedding,
        metadata={"governance_replay_relax_stage1_semantic": True},
    )

    cascade_trace: dict[str, Any] = {
        "stages_run": [],
        "execution_context": execution_context,
        "cascade_version": "2.0-hybrid-resplit-lab",
        "conflict_execution_profile": conflict_execution_profile,
    }

    deterministic_prune_set: set[str] = set()

    # ── Pre-cascade: same-key body diff ───────────────────────────────────
    pre_conflicts = _precascade_same_key_body_diff(proposal_key, proposal_body, ctx)
    pre_trace = {
        "lane": "precascade",
        "stage": 0,
        "conflicts_found": len(pre_conflicts),
        "latency_ms": 0.0,
    }
    cascade_trace["stages_run"].append(pre_trace)
    if pre_conflicts:
        apply_signal_contract(pre_conflicts)
        total_ms = round((time.monotonic() - t0) * 1000, 2)
        cascade_trace["total_latency_ms"] = total_ms
        cascade_trace["total_conflicts"] = len(pre_conflicts)
        cascade_trace["prune_set_size"] = 0
        cascade_trace["arbitration"] = {
            "winning_detector_plane": "deterministic",
            "final_conflict_type": "contradiction",
            "preflight_terminal": True,
        }
        return {
            "conflicts": pre_conflicts,
            "prune_set": set(),
            "deterministic_conflicts": pre_conflicts,
            "structural_conflicts": [],
            "semantic_conflicts": [],
            "semantic_trace": {},
            "structural_preflight": {"called": True, "classes_detected": ["contradiction"]},
            "lane_verdicts": {},
            "final_conflict_type": "contradiction",
            "winning_detector_plane": "deterministic",
            "preflight_terminal": True,
            "detector_disagreements": [],
            "signal_type": "conflict",
            "signal_contract_version": _SIGNAL_CONTRACT_VERSION,
            "authority_source": pre_conflicts[0].get("authority_source"),
            "evidence_set": list(pre_conflicts[0].get("evidence_set") or []),
            "recommended_action": pre_conflicts[0].get("recommended_action"),
            "cascade_trace": cascade_trace,
        }

    # ── Stage 1: Temporal ─────────────────────────────────────────────────
    t1 = time.monotonic()
    temporal_eng = TemporalInvalidationEngine()
    stage1_raw = temporal_eng.evaluate(proposal, ctx)
    stage1_conflicts = _findings_temporal_to_cascade(stage1_raw, proposal_key, ctx)
    deterministic_conflicts, temporal_nonterminal = split_temporal_conflicts(stage1_conflicts)
    update_prune_set(deterministic_prune_set, deterministic_conflicts, fact)
    stage1_trace = standardize_stage_trace(
        {
            "lane": "temporal",
            "stage": 1,
            "latency_ms": round((time.monotonic() - t1) * 1000, 2),
            "conflicts_found": len(stage1_conflicts),
            "deterministic_conflicts_found": len(deterministic_conflicts),
            "nonterminal_conflicts_found": len(temporal_nonterminal),
        },
        stage1_conflicts,
        fact,
        verification_depth="deterministic_temporal",
    )
    cascade_trace["stages_run"].append(stage1_trace)

    # ── Stage 2: Structured constraint ────────────────────────────────────
    t2 = time.monotonic()
    onto_eng = OntologyConstraintEngine()
    stage2_raw = onto_eng.evaluate(proposal, ctx)
    stage2_conflicts = _findings_constraints_to_cascade(stage2_raw, proposal_key)
    stage2_trace = standardize_stage_trace(
        {
            "lane": "constraint_structured",
            "stage": 2,
            "latency_ms": round((time.monotonic() - t2) * 1000, 2),
            "conflicts_found": len(stage2_conflicts),
        },
        stage2_conflicts,
        fact,
        verification_depth="rule_program",
    )
    cascade_trace["stages_run"].append(stage2_trace)

    # ── Stage 3: Dependency ───────────────────────────────────────────────
    t3 = time.monotonic()
    dep_eng = DependencyImpactEngine(min_inbound_sources=1)
    stage3_raw = dep_eng.evaluate(proposal, ctx)
    stage3_conflicts_all = _findings_dependency_to_cascade(stage3_raw, proposal_key)
    stage3_conflicts: list[dict[str, Any]] = []
    for c in stage3_conflicts_all:
        if conflict_pair_key(c, fact) not in deterministic_prune_set:
            stage3_conflicts.append(c)
    stage3_trace = standardize_stage_trace(
        {
            "lane": "dependency",
            "stage": 3,
            "latency_ms": round((time.monotonic() - t3) * 1000, 2),
            "conflicts_found": len(stage3_conflicts),
            "pairs_pruned": len(stage3_conflicts_all) - len(stage3_conflicts),
        },
        stage3_conflicts,
        fact,
        verification_depth="graph_program",
    )
    cascade_trace["stages_run"].append(stage3_trace)

    # ── Stage 4: Semantic constraint (NLI vs constraint facts) — lab stub ─
    t4 = time.monotonic()
    stage4_conflicts: list[dict[str, Any]] = []
    stage4_trace = standardize_stage_trace(
        {
            "lane": "constraint_semantic",
            "stage": 4,
            "latency_ms": round((time.monotonic() - t4) * 1000, 2),
            "conflicts_found": 0,
            "skipped": True,
            "note": "Lab stub: no constraint-kind KG facts wired offline",
        },
        [],
        fact,
        verification_depth="nli",
    )
    cascade_trace["stages_run"].append(stage4_trace)

    # ── Stage 5: Semantic contradiction (progressive pipeline) ───────────
    from spiral_semantic_stages.pipeline import check_semantic_contradictions_stages

    t5 = time.monotonic()
    semantic_trace: dict[str, Any] = {
        "pipeline": "progressive_semantic_lab",
        "execution_profile": conflict_execution_profile or "research",
        "execution_plane": "async" if execution_context == "post_write" else "preflight",
    }
    raw_hits = check_semantic_contradictions_stages(
        proposal_key,
        proposal_body,
        neighbor_dicts,
        settings=semantic_settings,
        trace=semantic_trace,
    )
    stage5_conflicts: list[dict[str, Any]] = []
    for h in raw_hits:
        ct = str(h.get("conflict_type") or "")
        if ct not in ("semantic_contradiction", "unverified_similarity"):
            continue
        det = dict(h.get("details") or {})
        det.setdefault("proposed_key", proposal_key)
        det.setdefault("lane_source", "semantic")
        det.setdefault(
            "detection_method",
            det.get("detection_method") or "progressive_semantic_pipeline",
        )
        nk = det.get("neighbor_key") or det.get("conflicting_fact_key") or ""
        c = {
            "conflict_type": ct,
            "severity": str(h.get("severity") or "high").lower(),
            "message": h.get("summary") or ct,
            "conflicting_fact_key": nk,
            "conflicting_fact_id": det.get("neighbor_id"),
            "details": det,
        }
        if conflict_pair_key(c, fact) in deterministic_prune_set:
            continue
        stage5_conflicts.append(c)

    stage5_trace = standardize_stage_trace(
        {
            "lane": "semantic_contradiction",
            "stage": 5,
            "latency_ms": round((time.monotonic() - t5) * 1000, 2),
            "conflicts_found": len(stage5_conflicts),
            "semantic_trace": semantic_trace,
            "total_candidates": len(raw_hits),
            "pruned_by_deterministic_stage": len(raw_hits) - len(stage5_conflicts),
        },
        stage5_conflicts,
        fact,
        verification_depth="llm_primary",
    )
    stage5_trace["temporal_alignment_pairs_pruned"] = len(deterministic_prune_set)
    cascade_trace["stages_run"].append(stage5_trace)

    structural_conflicts = deduplicate_cascade_conflicts(
        temporal_nonterminal + stage2_conflicts + stage3_conflicts + stage4_conflicts
    )
    semantic_conflicts = deduplicate_cascade_conflicts(stage5_conflicts)
    deterministic_conflicts_dedup = deduplicate_cascade_conflicts(deterministic_conflicts)

    arbitration = arbitrate_planes(
        fact=fact,
        deterministic_conflicts=deterministic_conflicts_dedup,
        structural_conflicts=structural_conflicts,
        semantic_conflicts=semantic_conflicts,
        semantic_trace=semantic_trace,
        execution_context=execution_context,
        stage_traces={
            "temporal": stage1_trace,
            "constraint_structured": stage2_trace,
            "dependency": stage3_trace,
            "constraint_semantic": stage4_trace,
            "semantic_contradiction": stage5_trace,
        },
    )
    apply_signal_contract(arbitration["conflicts"])
    apply_signal_contract(deterministic_conflicts_dedup)
    apply_signal_contract(structural_conflicts)
    apply_signal_contract(semantic_conflicts)

    total_ms = round((time.monotonic() - t0) * 1000, 2)
    cascade_trace["total_latency_ms"] = total_ms
    cascade_trace["total_conflicts"] = len(arbitration["conflicts"])
    cascade_trace["prune_set_size"] = len(deterministic_prune_set)
    cascade_trace["arbitration"] = {
        "winning_detector_plane": arbitration["winning_detector_plane"],
        "final_conflict_type": arbitration["final_conflict_type"],
        "preflight_terminal": arbitration["preflight_terminal"],
        "semantic_suppressed_same_pair": arbitration["semantic_suppressed_same_pair"],
        "structural_suppressed_same_pair": arbitration["structural_suppressed_same_pair"],
        "detector_disagreements": arbitration["detector_disagreements"],
    }

    final_conflicts = arbitration["conflicts"]
    primary = final_conflicts[0] if final_conflicts else None
    return {
        "conflicts": final_conflicts,
        "prune_set": deterministic_prune_set,
        "deterministic_conflicts": deterministic_conflicts_dedup,
        "structural_conflicts": structural_conflicts,
        "semantic_conflicts": semantic_conflicts,
        "semantic_trace": semantic_trace,
        "structural_preflight": arbitration["structural_preflight"],
        "lane_verdicts": arbitration["lane_verdicts"],
        "final_conflict_type": arbitration["final_conflict_type"],
        "winning_detector_plane": arbitration["winning_detector_plane"],
        "preflight_terminal": arbitration["preflight_terminal"],
        "detector_disagreements": arbitration["detector_disagreements"],
        "signal_type": "conflict",
        "signal_contract_version": _SIGNAL_CONTRACT_VERSION,
        "authority_source": primary.get("authority_source") if primary else None,
        "evidence_set": list(primary.get("evidence_set") or []) if primary else [],
        "recommended_action": primary.get("recommended_action") if primary else None,
        "cascade_trace": cascade_trace,
    }
