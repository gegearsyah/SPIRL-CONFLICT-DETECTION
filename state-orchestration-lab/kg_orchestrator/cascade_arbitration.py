"""
Vendored arbitration + cascade helpers aligned with Spiral
`backend/app/services/cascade_router.py` (hybrid re-split, v2.0).

Pure Python — no FastAPI / SQLAlchemy. Used by `cascade_lab.py` for offline RDL
evaluation that mirrors live preflight semantics (planes, prune_set, arbitration).
"""

from __future__ import annotations

from typing import Any

_STRUCTURAL_TYPES = frozenset(
    {
        "temporal_invalidation",
        "constraint_violation",
        "dependency_impact",
        "contradiction",
    }
)
_SEMANTIC_TYPES = frozenset({"semantic_contradiction", "unverified_similarity"})
_CONSTRAINT_KINDS = frozenset({"constraint", "rule", "policy", "governance"})
_DETERMINISTIC_TEMPORAL_METHODS = frozenset(
    {
        "temporal_lane_interval_overlap",
        "temporal_lane_inverted_window",
        "temporal_lane_transaction_anomaly",
        "temporal_lane_staleness",
    }
)
_SIGNAL_CONTRACT_VERSION = "rdl-signal-2026-04-v1"

_SEMANTIC_REJECT_STOPS = frozenset(
    {
        "forward_nli_non_contradiction",
        "forward_margin_failed",
        "forward_confidence_failed",
        "reverse_nli_non_contradiction",
        "reverse_margin_failed",
        "reverse_confidence_failed",
        "support_verifier_consistent",
        "support_verifier_uncertain",
    }
)
_SEMANTIC_ABSTAIN_STOPS = frozenset(
    {
        "support_verifier_unavailable",
        "unverified_similarity_emitted",
        "committee_disagreement_abstain",
    }
)

_TYPE_PRIORITY = {
    "temporal_invalidation": 1,
    "constraint_violation": 2,
    "dependency_impact": 3,
    "contradiction": 4,
    "semantic_contradiction": 5,
    "unverified_similarity": 6,
}
_SEVERITY_PRIORITY = {"critical": 0, "high": 1, "warning": 2, "medium": 3, "low": 4, "info": 5}


def pair_key(fact_a_id: str, fact_b_id: str) -> str:
    return "|".join(sorted([fact_a_id, fact_b_id]))


def conflict_pair_key(conflict: dict[str, Any], proposed_fact: dict[str, Any]) -> str:
    fact_id = str(proposed_fact.get("id") or proposed_fact.get("key") or "")
    neighbor_id = str(
        conflict.get("conflicting_fact_id")
        or conflict.get("conflicting_fact_key")
        or (conflict.get("details") or {}).get("neighbor_key")
        or ""
    )
    return pair_key(fact_id, neighbor_id)


def split_temporal_conflicts(
    conflicts: list[dict[str, Any]],
) -> tuple[list[dict], list[dict]]:
    deterministic: list[dict] = []
    nonterminal: list[dict] = []
    for conflict in conflicts:
        if is_deterministic_temporal_conflict(conflict):
            deterministic.append(conflict)
        else:
            nonterminal.append(conflict)
    return deterministic, nonterminal


def is_deterministic_temporal_conflict(conflict: dict[str, Any]) -> bool:
    if conflict.get("conflict_type") != "temporal_invalidation":
        return False
    details = conflict.get("details") or {}
    method = str(details.get("detection_method") or "").strip()
    return method in _DETERMINISTIC_TEMPORAL_METHODS


def update_prune_set(
    prune_set: set[str],
    conflicts: list[dict],
    proposed_fact: dict[str, Any],
) -> None:
    for conflict in conflicts:
        prune_set.add(conflict_pair_key(conflict, proposed_fact))


def is_explicit_structural_proof(conflict: dict[str, Any]) -> bool:
    ctype = str(conflict.get("conflict_type") or "")
    details = conflict.get("details") or {}
    if ctype == "dependency_impact":
        return bool(
            details.get("edge_path")
            or details.get("dependent_fact_id")
            or details.get("edge_type")
        )
    if ctype == "constraint_violation":
        lane = str(details.get("lane_source") or "")
        if lane == "constraint_structured":
            return bool(details.get("constraint_type") or details.get("constraint_label"))
        if lane == "constraint_semantic":
            return str(conflict.get("conflicting_fact_kind") or "").lower() in _CONSTRAINT_KINDS
        return False
    if ctype == "temporal_invalidation":
        method = str(details.get("detection_method") or "").strip()
        return method in _DETERMINISTIC_TEMPORAL_METHODS
    if ctype == "contradiction":
        return True
    return False


def semantic_lane_verdict(
    trace: dict[str, Any] | None,
    semantic_conflicts: list[dict[str, Any]],
) -> tuple[str, str | None]:
    emitted_conflicts = [
        c for c in semantic_conflicts if c.get("conflict_type") == "semantic_contradiction"
    ]
    if emitted_conflicts:
        return "detected", "emitted_contradiction"
    if not isinstance(trace, dict):
        return "unavailable", None

    stop_reason = trace.get("winning_stop_reason")
    try:
        emitted_count = int(trace.get("emitted_conflict_count") or 0)
    except (TypeError, ValueError):
        emitted_count = 0

    if emitted_count > 0 or stop_reason == "emitted_contradiction":
        return "detected", "emitted_contradiction"

    _pipeline = str(trace.get("pipeline") or "").strip()
    if _pipeline == "llm_primary":
        execution_profile = str(trace.get("execution_profile") or "interactive").strip().lower()
        if stop_reason == "llm_judge_contradiction":
            return "detected", str(stop_reason)
        trace_status = trace.get("trace_status")
        if trace_status == "unavailable" or stop_reason == "semantic_trace_unavailable":
            return "unavailable", str(stop_reason) if stop_reason else None
        if stop_reason == "no_retrieval_candidates":
            return "rejected", str(stop_reason)
        if stop_reason == "judge_budget_exhausted":
            if execution_profile == "research":
                return "abstain", str(stop_reason)
            return "rejected", str(stop_reason)
        if stop_reason in {
            "llm_judge_consistent",
            "llm_judge_uncertain",
            "fast_filter_entailment",
        }:
            return "rejected", str(stop_reason)
        if trace_status == "degraded":
            return "abstain", str(stop_reason)
        return "rejected", str(stop_reason)

    trace_status = trace.get("trace_status")
    if trace_status == "unavailable" or stop_reason == "semantic_trace_unavailable":
        return "unavailable", str(stop_reason) if stop_reason else None
    if stop_reason in _SEMANTIC_ABSTAIN_STOPS:
        return "abstain", str(stop_reason)
    if stop_reason in _SEMANTIC_REJECT_STOPS:
        return "rejected", str(stop_reason)
    if trace_status == "degraded":
        return "abstain", str(stop_reason)
    return "unavailable", str(stop_reason) if stop_reason else None


def structural_stage_checked(stage_traces: dict[str, dict[str, Any]]) -> bool:
    for lane in ("temporal", "constraint_structured", "dependency", "constraint_semantic"):
        trace = stage_traces.get(lane) or {}
        if not trace.get("error"):
            return True
    return False


def best_conflict_by_pair(
    conflicts: list[dict[str, Any]],
    proposed_fact: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    best: dict[str, dict[str, Any]] = {}
    for conflict in conflicts:
        pair = conflict_pair_key(conflict, proposed_fact)
        existing = best.get(pair)
        if existing is None or conflict_priority(conflict) < conflict_priority(existing):
            best[pair] = conflict
    return best


def best_overall_conflict(conflicts: list[dict[str, Any]]) -> dict[str, Any]:
    return sorted(conflicts, key=conflict_priority)[0]


def annotate_lane_authority(conflict: dict[str, Any], reason: str) -> dict[str, Any]:
    details = dict(conflict.get("details") or {})
    details["lane_authority_reason"] = reason
    conflict["details"] = details
    return conflict


def arbitrate_planes(
    *,
    fact: dict[str, Any],
    deterministic_conflicts: list[dict[str, Any]],
    structural_conflicts: list[dict[str, Any]],
    semantic_conflicts: list[dict[str, Any]],
    semantic_trace: dict[str, Any] | None,
    execution_context: str = "preflight",  # reserved for parity with Spiral router
    stage_traces: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    _ = execution_context  # preflight vs post_write handled in live Spiral Stage 5 only
    deterministic_pairs = {conflict_pair_key(c, fact) for c in deterministic_conflicts}
    structural_by_pair = best_conflict_by_pair(structural_conflicts, fact)
    semantic_by_pair = best_conflict_by_pair(semantic_conflicts, fact)

    final_conflicts: list[dict[str, Any]] = list(deterministic_conflicts)
    kept_structural: list[dict[str, Any]] = []
    kept_semantic: list[dict[str, Any]] = []
    semantic_suppressed_same_pair = 0
    structural_suppressed_same_pair = 0
    disagreements: list[dict[str, Any]] = []

    all_pairs = sorted(set(structural_by_pair) | set(semantic_by_pair))
    for pair in all_pairs:
        structural = structural_by_pair.get(pair)
        semantic = semantic_by_pair.get(pair)
        if pair in deterministic_pairs:
            if semantic or structural:
                disagreements.append(
                    {
                        "pair_key": pair,
                        "reason": "deterministic_terminal_pair",
                        "structural_type": structural.get("conflict_type") if structural else None,
                        "semantic_type": semantic.get("conflict_type") if semantic else None,
                    }
                )
            continue
        if structural and semantic:
            if is_explicit_structural_proof(structural):
                kept_structural.append(
                    annotate_lane_authority(structural, "structural_explicit_proof")
                )
                semantic_suppressed_same_pair += 1
                disagreements.append(
                    {
                        "pair_key": pair,
                        "reason": "structural_explicit_proof_beats_semantic",
                        "structural_type": structural.get("conflict_type"),
                        "semantic_type": semantic.get("conflict_type"),
                    }
                )
            else:
                kept_semantic.append(
                    annotate_lane_authority(semantic, "semantic_beats_weak_structural")
                )
                structural_suppressed_same_pair += 1
                disagreements.append(
                    {
                        "pair_key": pair,
                        "reason": "weak_structural_suppressed",
                        "structural_type": structural.get("conflict_type"),
                        "semantic_type": semantic.get("conflict_type"),
                    }
                )
            continue
        if structural:
            kept_structural.append(structural)
            continue
        if semantic:
            kept_semantic.append(semantic)

    final_conflicts.extend(kept_structural)
    final_conflicts.extend(kept_semantic)
    final_conflicts = deduplicate_cascade_conflicts(final_conflicts)

    winning_plane = "none"
    final_conflict_type: str | None = None
    if deterministic_conflicts:
        winning_plane = "deterministic"
        final_conflict_type = best_overall_conflict(deterministic_conflicts).get("conflict_type")
    elif kept_structural:
        winning_plane = "structural"
        final_conflict_type = best_overall_conflict(kept_structural).get("conflict_type")
    elif kept_semantic:
        winning_plane = "semantic"
        final_conflict_type = best_overall_conflict(kept_semantic).get("conflict_type")

    semantic_verdict, semantic_stop_reason = semantic_lane_verdict(semantic_trace, semantic_conflicts)
    structural_preflight = build_structural_preflight(
        deterministic_conflicts=deterministic_conflicts,
        structural_conflicts=structural_conflicts,
        kept_structural=kept_structural,
        stage_traces=stage_traces,
    )
    lane_verdicts = {
        "deterministic": {
            "verdict": "detected" if deterministic_conflicts else "clear",
            "detected_types": sorted(
                {
                    str(c.get("conflict_type") or "")
                    for c in deterministic_conflicts
                    if c.get("conflict_type")
                }
            ),
        },
        "structural": {
            "verdict": (
                "detected"
                if kept_structural or deterministic_conflicts
                else (
                    "rejected"
                    if structural_conflicts or structural_stage_checked(stage_traces)
                    else "unavailable"
                )
            ),
            "detected_types": sorted(
                {
                    str(c.get("conflict_type") or "")
                    for c in kept_structural + deterministic_conflicts
                    if c.get("conflict_type") in _STRUCTURAL_TYPES
                }
            ),
            "suppressed_same_pair": structural_suppressed_same_pair,
        },
        "semantic": {
            "verdict": semantic_verdict,
            "stop_reason": semantic_stop_reason,
            "detected_types": sorted(
                {
                    str(c.get("conflict_type") or "")
                    for c in kept_semantic
                    if c.get("conflict_type") in _SEMANTIC_TYPES
                }
            ),
            "suppressed_same_pair": semantic_suppressed_same_pair,
        },
    }

    preflight_terminal = bool(final_conflicts)
    if not preflight_terminal:
        if semantic_verdict == "rejected" and structural_stage_checked(stage_traces):
            preflight_terminal = True
        elif semantic_verdict == "abstain":
            preflight_terminal = False
        elif semantic_verdict == "unavailable":
            preflight_terminal = False
        elif structural_stage_checked(stage_traces):
            preflight_terminal = True

    return {
        "conflicts": final_conflicts,
        "structural_preflight": structural_preflight,
        "lane_verdicts": lane_verdicts,
        "winning_detector_plane": winning_plane,
        "final_conflict_type": final_conflict_type,
        "preflight_terminal": preflight_terminal,
        "semantic_suppressed_same_pair": semantic_suppressed_same_pair,
        "structural_suppressed_same_pair": structural_suppressed_same_pair,
        "detector_disagreements": disagreements,
    }


def best_conflict_by_type(conflicts: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    best: dict[str, dict[str, Any]] = {}
    for conflict in conflicts:
        ctype = str(conflict.get("conflict_type") or "")
        existing = best.get(ctype)
        if existing is None or conflict_priority(conflict) < conflict_priority(existing):
            best[ctype] = conflict
    return best


def build_structural_preflight(
    *,
    deterministic_conflicts: list[dict[str, Any]],
    structural_conflicts: list[dict[str, Any]],
    kept_structural: list[dict[str, Any]],
    stage_traces: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    structural_all = deterministic_conflicts + structural_conflicts
    classes_detected = sorted(
        {
            str(c.get("conflict_type") or "")
            for c in structural_all
            if c.get("conflict_type") in _STRUCTURAL_TYPES
        }
    )

    verdicts: dict[str, str] = {}
    reasoning_confidence: dict[str, str | None] = {}
    route_confidence: dict[str, str | None] = {}
    abstained_reason: dict[str, str | None] = {}
    stop_reasons: dict[str, str | None] = {}
    structural_anchor_fact_id: dict[str, str | None] = {}
    match_result: dict[str, str] = {}
    search_result: dict[str, str] = {}
    verify_result: dict[str, str] = {}
    graph_program_path: dict[str, list[str]] = {}

    detected_map = best_conflict_by_type(structural_all)
    kept_types = {str(c.get("conflict_type") or "") for c in kept_structural + deterministic_conflicts}
    stage_for_type = {
        "temporal_invalidation": ["temporal"],
        "constraint_violation": ["constraint_structured", "constraint_semantic"],
        "dependency_impact": ["dependency"],
    }
    for conflict_type in ("dependency_impact", "constraint_violation", "temporal_invalidation"):
        winner = detected_map.get(conflict_type)
        traces = [stage_traces.get(name) or {} for name in stage_for_type.get(conflict_type, [])]
        error_only = traces and all(bool(t.get("error")) for t in traces)
        ran_successfully = any(not t.get("error") for t in traces)

        if conflict_type in kept_types and winner is not None:
            verdicts[conflict_type] = "detected"
            reasoning_confidence[conflict_type] = "high"
            route_confidence[conflict_type] = "high"
            stop_reasons[conflict_type] = "detected"
            abstained_reason[conflict_type] = None
            structural_anchor_fact_id[conflict_type] = (
                str(winner.get("conflicting_fact_id"))
                if winner.get("conflicting_fact_id") is not None
                else None
            )
            match_result[conflict_type] = "matched"
            search_result[conflict_type] = "hit"
            verify_result[conflict_type] = "verified"
        elif error_only:
            verdicts[conflict_type] = "unavailable"
            reasoning_confidence[conflict_type] = None
            route_confidence[conflict_type] = None
            stop_reasons[conflict_type] = "stage_error"
            abstained_reason[conflict_type] = "stage_error"
            structural_anchor_fact_id[conflict_type] = None
            match_result[conflict_type] = "error"
            search_result[conflict_type] = "error"
            verify_result[conflict_type] = "error"
        elif ran_successfully:
            verdicts[conflict_type] = "rejected"
            reasoning_confidence[conflict_type] = "medium"
            route_confidence[conflict_type] = "medium"
            stop_reasons[conflict_type] = f"no_{conflict_type}_proof"
            abstained_reason[conflict_type] = None
            structural_anchor_fact_id[conflict_type] = None
            match_result[conflict_type] = "no_match"
            search_result[conflict_type] = "checked"
            verify_result[conflict_type] = "no_proof"
        else:
            verdicts[conflict_type] = "abstain"
            reasoning_confidence[conflict_type] = None
            route_confidence[conflict_type] = None
            stop_reasons[conflict_type] = "not_invoked"
            abstained_reason[conflict_type] = "not_invoked"
            structural_anchor_fact_id[conflict_type] = None
            match_result[conflict_type] = "not_invoked"
            search_result[conflict_type] = "not_invoked"
            verify_result[conflict_type] = "not_invoked"
        graph_program_path[conflict_type] = ["match", "search", "verify"]

    dependency_paths: list[str] = []
    for conflict in structural_all:
        if conflict.get("conflict_type") == "dependency_impact":
            for node in (conflict.get("details") or {}).get("edge_path") or []:
                node_s = str(node)
                if node_s and node_s not in dependency_paths:
                    dependency_paths.append(node_s)

    constraint_slots: list[str] = []
    for conflict in structural_all:
        if conflict.get("conflict_type") == "constraint_violation":
            label = str((conflict.get("details") or {}).get("constraint_label") or "")
            ctype = str((conflict.get("details") or {}).get("constraint_type") or "")
            token = ":".join(part for part in (ctype, label) if part)
            if token and token not in constraint_slots:
                constraint_slots.append(token)

    temporal_cues: list[str] = []
    for conflict in structural_all:
        if conflict.get("conflict_type") == "temporal_invalidation":
            method = str((conflict.get("details") or {}).get("detection_method") or "")
            if method and method not in temporal_cues:
                temporal_cues.append(method)

    return {
        "called": True,
        "classes_detected": classes_detected,
        "detector_versions": {
            "dependency_impact": "dependency_lab_v1",
            "constraint_violation": "constraint_lab_v1",
            "temporal_invalidation": "temporal_lab_v1",
        },
        "stop_reasons": stop_reasons,
        "dependency_path_used": dependency_paths,
        "constraint_slots_compared": constraint_slots,
        "temporal_regression_cues": temporal_cues,
        "verdicts": verdicts,
        "reasoning_confidence": reasoning_confidence,
        "abstained_reason": abstained_reason,
        "route_confidence": route_confidence,
        "match_result": match_result,
        "search_result": search_result,
        "verify_result": verify_result,
        "graph_program_path": graph_program_path,
        "structural_anchor_fact_id": structural_anchor_fact_id,
        "conflicts": structural_all,
    }


def authority_source(conflict: dict[str, Any]) -> str:
    details = conflict.get("details") or {}
    conflict_type = str(conflict.get("conflict_type") or "")
    lane_source = str(details.get("lane_source") or "")
    method = str(details.get("detection_method") or "")
    if conflict_type == "temporal_invalidation":
        return "temporal_lane_sql"
    if conflict_type == "constraint_violation":
        if lane_source == "constraint_structured":
            return "project_constraints"
        if lane_source == "constraint_semantic":
            return "constraint_fact_nli"
    if conflict_type == "dependency_impact":
        return "dependency_graph_path" if details.get("edge_path") else "dependency_graph_lookup"
    if conflict_type == "semantic_contradiction":
        if "llm" in method or lane_source == "semantic":
            return "semantic_llm_judge"
        return "semantic_verifier"
    if conflict_type == "contradiction":
        return "same_key_body_diff"
    return lane_source or "detector"


def evidence_set(conflict: dict[str, Any]) -> list[str]:
    details = conflict.get("details") or {}
    evidence: list[str] = []
    conflict_type = str(conflict.get("conflict_type") or "")
    lane_source = str(details.get("lane_source") or "")
    if conflict_type == "temporal_invalidation":
        evidence.extend(["valid_from", "valid_until"])
        method = str(details.get("detection_method") or "")
        if method:
            evidence.append(method)
    elif conflict_type == "constraint_violation":
        if lane_source == "constraint_structured":
            evidence.extend(["project_constraints", "structured_slot_compare"])
            if details.get("constraint_type"):
                evidence.append(f"constraint_type:{details.get('constraint_type')}")
        else:
            evidence.extend(["constraint_fact", "nli_verification"])
    elif conflict_type == "dependency_impact":
        evidence.append("graph_path")
        if details.get("edge_type"):
            evidence.append(f"edge_type:{details.get('edge_type')}")
        if details.get("traversal_depth") is not None:
            evidence.append(f"depth:{details.get('traversal_depth')}")
    elif conflict_type == "semantic_contradiction":
        evidence.extend(["hybrid_retrieval", "semantic_trace", "llm_judge"])
    elif conflict_type == "contradiction":
        evidence.extend(["same_key", "body_diff"])
    return evidence


def recommended_action(conflict: dict[str, Any]) -> str:
    conflict_type = str(conflict.get("conflict_type") or "")
    if conflict_type == "temporal_invalidation":
        return "review_fact_timeline"
    if conflict_type == "constraint_violation":
        return "review_violated_rule"
    if conflict_type == "dependency_impact":
        return "review_downstream_impacts"
    if conflict_type == "semantic_contradiction":
        return "open_conflict_proposal"
    if conflict_type == "contradiction":
        return "resolve_same_key_rewrite"
    return "review_conflict"


def apply_signal_contract(conflicts: list[dict[str, Any]]) -> None:
    for conflict in conflicts:
        details = dict(conflict.get("details") or {})
        auth = authority_source(conflict)
        ev = evidence_set(conflict)
        rec = recommended_action(conflict)
        conflict["signal_type"] = "conflict"
        conflict["signal_contract_version"] = _SIGNAL_CONTRACT_VERSION
        conflict["authority_source"] = auth
        conflict["evidence_set"] = ev
        conflict["recommended_action"] = rec
        details.setdefault("authority_source", auth)
        details.setdefault("evidence_set", ev)
        details.setdefault("recommended_action", rec)
        conflict["details"] = details


def conflict_priority(conflict: dict) -> tuple[int, int]:
    ctype = str(conflict.get("conflict_type") or "unknown")
    severity = str(conflict.get("severity") or "info")
    return (
        _TYPE_PRIORITY.get(ctype, 99),
        _SEVERITY_PRIORITY.get(severity, 99),
    )


def deduplicate_cascade_conflicts(conflicts: list[dict]) -> list[dict]:
    structural: list[dict] = []
    semantic: list[dict] = []
    for conflict in conflicts:
        ctype = str(conflict.get("conflict_type") or "")
        if ctype in _SEMANTIC_TYPES:
            semantic.append(conflict)
        else:
            structural.append(conflict)

    pair_best: dict[str, dict] = {}
    for conflict in structural:
        proposed_key = str((conflict.get("details") or {}).get("proposed_key") or "")
        neighbor_key = str(
            conflict.get("conflicting_fact_key") or conflict.get("conflicting_fact_id") or ""
        )
        pair = f"{proposed_key}|{neighbor_key}"
        existing = pair_best.get(pair)
        if existing is None or conflict_priority(conflict) < conflict_priority(existing):
            pair_best[pair] = conflict

    key_best: dict[str, dict] = {}
    for conflict in semantic:
        proposed_key = str(
            (conflict.get("details") or {}).get("proposed_key")
            or conflict.get("conflicting_fact_key")
            or ""
        )
        existing = key_best.get(proposed_key)
        if existing is None or conflict_priority(conflict) < conflict_priority(existing):
            key_best[proposed_key] = conflict

    return list(pair_best.values()) + list(key_best.values())


def standardize_stage_trace(
    trace: dict[str, Any],
    conflicts: list[dict[str, Any]],
    proposed_fact: dict[str, Any],
    *,
    verification_depth: str,
) -> dict[str, Any]:
    normalized = dict(trace)
    normalized["candidates_considered"] = len(conflicts) or int(
        normalized.get("candidates_considered") or 0
    )
    normalized["pairs_pruned"] = int(normalized.get("pairs_pruned") or 0)
    normalized["pairs_emitted"] = len(
        {conflict_pair_key(conflict, proposed_fact) for conflict in conflicts}
    )
    normalized["degraded_mode"] = (
        "error"
        if trace.get("error")
        else ("skipped" if trace.get("skipped") else str(trace.get("degraded_mode") or "none"))
    )
    normalized["verification_depth"] = str(
        normalized.get("verification_depth") or verification_depth
    )
    return normalized
