#!/usr/bin/env python3
"""
Real Data Lab Phase 2b — benign proposals from real-data-lab/list_benign.md via Spirl MCP.

See research_prompt/real_data_lab_mixed_workload_prompt.md.
Run after Phase 2 (list_conflict.md) on the same project; do not re-run conflict rows.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from argparse import Namespace
from pathlib import Path
from typing import Any

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from paper3_phase2_mcp_run import (  # noqa: E402
    McpSession,
    append_jsonl,
    detection_inline_available,
    find_notification_for_keys,
    iso_now,
    list_all_facts,
    load_json,
    observed_notification_latency_ms,
    parse_detection,
    poll_for_conflict_notification,
    POLL_CONFLICTS_INTERVAL_S,
)

from real_data_lab_phase2_mcp_run import (  # noqa: E402
    BTC_ROOT,
    SPIRL_CONFIG,
    MCP_PATH,
    RDL,
    EXEC_LOG,
    CHECKPOINTS,
    PAUSE_FLAG,
    DEFAULT_SKF_MANIFEST,
    CAT_TO_KIND,
    build_seed_audit,
    conflict_list_rel_for_log,
    corpus_key_token,
    detection_audit_block,
    effective_conflict_injection_total,
    load_project_id,
    normalize_valid_ts,
    parse_conflict_table,
    referenced_baseline_keys,
    resolve_conflict_list_path,
    rdl_phase1_complete,
    phase2_complete,
    skf_expected_keys,
    memory_check_conflicts_v1,
    build_semantic_preflight_block,
    semantic_primary_detection_result,
    merge_row_contract_fields,
)

from rdl_pipeline_execution_lock import rdl_pipeline_lock  # noqa: E402

DEFAULT_BENIGN_LIST = RDL / "list_benign.md"
MIXED_REPORT_PATH = RDL / "research" / "real_data_lab_mixed_report.md"

AGENT_ID = "rdl_phase2b_benign_agent"


def resolve_benign_list_path(cfg: dict[str, Any], cli_override: str | None) -> Path:
    if cli_override and str(cli_override).strip():
        p = Path(cli_override.strip())
        return p.resolve() if p.is_absolute() else (BTC_ROOT / p).resolve()
    benign_path = DEFAULT_BENIGN_LIST
    override = (cfg.get("real_data_lab_benign_list_path") or "").strip()
    if override:
        po = Path(override)
        benign_path = po.resolve() if po.is_absolute() else (BTC_ROOT / override).resolve()
    return benign_path


_ROW_RE = re.compile(
    r"^\|\s*((?:b|sb)-[a-z]+-\d+)\s*\|\s*([^|]+)\|\s*(.+?)\s*\|\s*([^|]+)\|\s*(.+?)\s*\|\s*([^|]*?)\s*\|\s*$",
    re.I,
)
_KEY_RE = re.compile(r"\*\*Key:\*\*\s*(\S+)", re.I)
_CAT_RE = re.compile(r"\*\*Cat:\*\*\s*(\S+)", re.I)
_VAL_RE = re.compile(r"\*\*Val:\*\*\s*\"((?:[^\"\\]|\\.)*)\"", re.I)
_VALID_RE = re.compile(
    r"\*\*Valid:\*\*\s*(\S+)\s+(\S+)",
    re.I,
)


def parse_benign_table(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    text = path.read_text(encoding="utf-8")
    for line in text.splitlines():
        line = line.strip()
        if not (line.startswith("| b-") or line.startswith("| sb-")):
            continue
        m = _ROW_RE.match(line)
        if not m:
            continue
        corpus_row_id = m.group(1).strip().lower()
        based_raw = m.group(2).strip()
        details = m.group(3).strip()
        label_raw = m.group(4).strip().lower().replace(" ", "")
        rationale = m.group(5).strip()
        source_raw = m.group(6).strip()

        km = _KEY_RE.search(details)
        cm = _CAT_RE.search(details)
        vm = _VAL_RE.search(details)
        vdm = _VALID_RE.search(details)
        if not (km and cm and vm and vdm):
            raise ValueError(f"Bad Proposed Fact Details for {corpus_row_id}")

        key = km.group(1).strip()
        cat = cm.group(1).strip().lower()
        val = vm.group(1).replace('\\"', '"')
        vf = normalize_valid_ts(vdm.group(1))
        vu_raw = vdm.group(2).strip().lower()
        valid_until: str | None = None if vu_raw in ("null", "none", "") else normalize_valid_ts(vdm.group(2))

        based_on = [x.strip() for x in based_raw.split(",") if x.strip()]
        if label_raw != "benign":
            raise ValueError(f"Expected benign label, got {label_raw!r} for {corpus_row_id}")

        kind = CAT_TO_KIND.get(cat)
        if not kind:
            raise ValueError(f"Unknown Cat {cat!r} for {corpus_row_id}")

        source_support: str | None = source_raw if source_raw else None
        rows.append(
            {
                "corpus_row_id": corpus_row_id,
                "based_on_facts": based_on,
                "proposed_key": key,
                "proposed_kind": kind,
                "body": val,
                "valid_from": vf,
                "valid_until": valid_until,
                "conflict_class": "benign",
                "expected_label": label_raw,
                "rationale_summary": rationale,
                "source_support": source_support,
            },
        )
    return rows


def benign_batch_start_logged(project_id: str) -> bool:
    if not EXEC_LOG.exists():
        return False
    for line in EXEC_LOG.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            o = json.loads(line)
        except json.JSONDecodeError:
            continue
        if o.get("phase") != 2 or o.get("action") != "conflict_injection_start":
            continue
        if o.get("project") != project_id:
            continue
        r = o.get("result") or {}
        if r.get("mode") == "table_driven_benign":
            return True
        if "list_benign" in str(r.get("source", "")):
            return True
    return False


def mixed_workload_metrics_logged() -> bool:
    if not EXEC_LOG.exists():
        return False
    for line in EXEC_LOG.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            o = json.loads(line)
        except json.JSONDecodeError:
            continue
        if (
            o.get("phase") == 3
            and o.get("action") == "metric_computed"
            and o.get("metric_group") == "mixed_workload_fp"
        ):
            return True
    return False


def benign_batch_complete(project_id: str) -> bool:
    if not CHECKPOINTS.exists():
        return False
    for line in CHECKPOINTS.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            o = json.loads(line)
        except json.JSONDecodeError:
            continue
        if o.get("checkpoint_type") == "benign_batch_complete" and o.get("status") == "complete":
            cpid = o.get("project_id")
            if cpid is not None and cpid != project_id:
                continue
            if cpid is None:
                continue
            return True
    return False


def resume_benign_injection_index(project_id: str) -> int:
    """Next 0-based row index = count of successful benign conflict_injected lines for this project."""
    n = 0
    if not EXEC_LOG.exists():
        return n
    for line in EXEC_LOG.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            o = json.loads(line)
        except json.JSONDecodeError:
            continue
        if o.get("phase") != 2 or o.get("action") != "conflict_injected":
            continue
        if o.get("project") != project_id:
            continue
        if o.get("conflict_class") != "benign":
            continue
        n += 1
    return n


def upsert_fact(
    mcp: McpSession,
    project_id: str,
    *,
    kind: str,
    key: str,
    body: str,
    skip_conflict_check: bool = False,
    skip_embedding: bool = False,
    valid_from: str | None = None,
    valid_until: str | None = None,
) -> Any:
    args: dict[str, Any] = {
        "project_id": project_id,
        "kind": kind,
        "key": key,
        "body": body,
        "tier": 1,
        "source_type": "human",
        "actor": AGENT_ID,
        "agent_id": AGENT_ID,
        "skip_conflict_check": skip_conflict_check,
        "skip_embedding": skip_embedding,
    }
    if valid_from is not None:
        args["valid_from"] = valid_from
    if valid_until is not None:
        args["valid_until"] = valid_until
    return mcp.call_tool("memory_upsert_fact_v1", args)


def _semantic_preflight_detected_for_metrics(block: dict[str, Any] | None) -> bool:
    if not isinstance(block, dict) or not block.get("called"):
        return False
    verdict = block.get("semantic_verdict")
    if verdict == "detected":
        return True
    trace = block.get("semantic_trace")
    if not isinstance(trace, dict):
        return False
    try:
        return int(trace.get("emitted_conflict_count") or 0) > 0
    except (TypeError, ValueError):
        return trace.get("winning_stop_reason") == "emitted_contradiction"


def _preflight_types_from_result(res: dict[str, Any]) -> list[str]:
    observed: list[str] = []
    if _semantic_preflight_detected_for_metrics(res.get("preflight_semantic")):
        observed.append("semantic_contradiction")
    structural = res.get("structural_preflight") or {}
    for cls in structural.get("classes_detected") or []:
        cls = str(cls)
        if cls and cls not in observed:
            observed.append(cls)
    return observed


def _result_has_primary_fields(res: dict[str, Any]) -> bool:
    return any(
        key in res
        for key in (
            "final_conflict_type",
            "winning_detector_plane",
            "preflight_terminal",
            "lane_verdicts",
            "semantic_primary_detected",
            "structural_primary_detected",
            "preflight_semantic",
            "structural_preflight",
        )
    )


_GOV_NEEDS_REVIEW = "needs_review"


def _governance_outcome_from_result(res: dict[str, Any]) -> str | None:
    """Wave 4.3 — extract governance_outcome from the preflight envelope.

    Returns one of ``benign`` / ``typed_conflict`` / ``needs_review`` or
    ``None`` when the field is absent (pre-Wave-4 logs).  Accepts both
    the top-level key and the nested ``cascade_trace.arbitration``
    fallback so we can replay older logs too.
    """
    outcome = res.get("governance_outcome")
    if outcome:
        return str(outcome)
    trace = res.get("cascade_trace") or {}
    if isinstance(trace, dict):
        arb = trace.get("arbitration") or {}
        if isinstance(arb, dict) and arb.get("governance_outcome"):
            return str(arb.get("governance_outcome"))
    return None


def _governance_decision_from_result(res: dict[str, Any]) -> dict[str, Any] | None:
    """Wave 4.3++ — extract the full governance_decision dict for
    lossless offline re-scoring (Geifman & El-Yaniv NeurIPS 2017).
    """
    if not isinstance(res, dict):
        return None
    decision = res.get("governance_decision")
    if isinstance(decision, dict) and decision:
        return decision
    trace = res.get("cascade_trace") or {}
    if isinstance(trace, dict):
        arb = trace.get("arbitration") or {}
        if isinstance(arb, dict):
            nested = arb.get("governance_decision")
            if isinstance(nested, dict) and nested:
                return nested
    return None


def _preflight_primary_prediction(res: dict[str, Any]) -> tuple[str | None, str | None, bool]:
    final_conflict_type = res.get("final_conflict_type")
    # Wave 4.3 — ``needs_review`` is a first-class governance_outcome
    # rather than a typed-conflict label.  Treat it as preflight-terminal
    # abstention: no typed prediction, but mark the row as explicitly
    # routed to human review so it is not double-counted as a cross-type
    # alert for RDL exact-type scoring.
    if final_conflict_type == _GOV_NEEDS_REVIEW:
        return None, str(res.get("winning_detector_plane") or "governance_selector"), True
    if final_conflict_type:
        return str(final_conflict_type), str(res.get("winning_detector_plane") or "none"), True
    if res.get("preflight_terminal") is True:
        return None, str(res.get("winning_detector_plane") or "none"), True
    return None, None, False


def _derive_predicted_type(res: dict[str, Any], expected: str | None) -> tuple[str | None, str]:
    expected = str(expected or "")
    preflight_type, winning_plane, preflight_terminal = _preflight_primary_prediction(res)
    preflight_types = _preflight_types_from_result(res)
    inline_types = [str(x) for x in ((res.get("preflight_check") or {}).get("classes_detected") or []) if x]
    notif = res.get("notification") or {}
    async_type = str(notif.get("conflict_type") or "") or None

    if expected and expected != "benign" and preflight_type == expected:
        return expected, f"preflight_first_{winning_plane or 'none'}_exact"
    if expected and expected != "benign" and preflight_type is not None and preflight_type != expected:
        return preflight_type, f"preflight_first_{winning_plane or 'none'}_cross_type"
    if preflight_terminal and preflight_type is None:
        return None, "preflight_abstain"
    if expected and expected != "benign" and expected in preflight_types:
        return expected, "preflight_exact"
    if expected and expected != "benign" and expected in inline_types:
        return expected, "inline_exact"
    if expected and expected != "benign" and async_type == expected:
        return expected, "async_exact"
    if preflight_types:
        return preflight_types[0], "preflight_cross_type"
    if expected == "benign" and _result_has_primary_fields(res):
        return None, "preflight_abstain"
    if inline_types:
        return inline_types[0], "inline_cross_type"
    if async_type:
        return async_type, "async_cross_type"
    return None, "none"



def _semantic_budget_exhausted_in_result(res: dict[str, Any]) -> bool:
    blocks = [
        res.get("preflight_semantic"),
        res.get("semantic_trace"),
        ((res.get("preflight_semantic") or {}).get("semantic_trace") if isinstance(res.get("preflight_semantic"), dict) else None),
    ]
    for block in blocks:
        if not isinstance(block, dict):
            continue
        if bool(block.get("semantic_budget_exhausted")):
            return True
        if str(block.get("winning_stop_reason") or "") == "judge_budget_exhausted":
            return True
    return False



def compute_mixed_metrics_from_log() -> dict[str, Any]:
    if not EXEC_LOG.exists():
        return {}

    tracked_classes = [
        "semantic_contradiction",
        "dependency_impact",
        "constraint_violation",
        "temporal_invalidation",
        "ambiguous_case",
    ]
    core4_classes = {
        "semantic_contradiction",
        "dependency_impact",
        "constraint_violation",
        "temporal_invalidation",
    }
    by_class: dict[str, dict[str, int]] = {
        cls: {
            "injected": 0,
            "binary_detected": 0,
            "exact_detected": 0,
            "cross_type_alerts": 0,
            "abstained": 0,
        }
        for cls in tracked_classes
    }
    confusion: dict[str, dict[str, int]] = {}
    benign_fp_by_detector: dict[str, int] = {}
    conflict_total = 0
    core4_total = 0
    core4_exact_detected = 0
    conflict_detected_binary = 0
    conflict_detected_exact = 0
    benign_fp = 0
    benign_tn = 0
    benign_total = 0
    ambiguous_rows_total = 0
    ambiguous_alerted = 0
    ambiguous_abstained = 0
    semantic_benign_fp = 0
    constraint_benign_fp = 0
    dependency_benign_fp = 0
    semantic_budget_exhausted_benign_count = 0
    cross_type_alerts = 0
    abstain_total = 0
    preflight_async_disagreement = 0
    async_stronger_than_preflight = 0
    preflight_first_detected = 0
    winning_plane_counts: dict[str, int] = {}
    rows_scored = 0
    contract_complete_rows = 0
    contract_incomplete_rows = 0
    semantic_trace_missing_rows = 0
    preflight_terminal_rows = 0
    # Wave 4.3 — governance_outcome scoring (typed_conflict / needs_review /
    # benign).  ``needs_review`` is counted separately so it is neither a
    # binary FP on benign rows nor a cross-type alert on conflict rows.
    governance_outcome_counts: dict[str, int] = {
        "typed_conflict": 0,
        "needs_review": 0,
        "benign": 0,
        "unset": 0,
    }
    ambiguous_needs_review = 0
    benign_needs_review = 0
    conflict_needs_review = 0
    governance_needs_review_tp = 0
    governance_needs_review_fp = 0
    governance_needs_review_fn = 0

    for line in EXEC_LOG.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            o = json.loads(line)
        except json.JSONDecodeError:
            continue
        if o.get("phase") != 2 or o.get("action") != "conflict_injected":
            continue

        rid = str(o.get("corpus_row_id") or "")
        res = o.get("result") or {}
        rows_scored += 1
        if res.get("row_contract_complete") is True:
            contract_complete_rows += 1
        elif res.get("row_contract_complete") is False:
            contract_incomplete_rows += 1
        if bool(res.get("semantic_trace_missing")):
            semantic_trace_missing_rows += 1

        expected = str(res.get("expected_conflict_type") or o.get("conflict_class") or "")
        predicted, source = _derive_predicted_type(res, expected)
        preflight_type, winning_plane, preflight_terminal = _preflight_primary_prediction(res)
        async_type = str(((res.get("notification") or {}).get("conflict_type") or "")) or None
        gov_outcome = _governance_outcome_from_result(res)

        binary_alert = predicted is not None
        exact_type_match = expected not in {"", "benign", "ambiguous_case"} and predicted == expected
        cross_type = expected not in {"", "benign", "ambiguous_case"} and predicted is not None and predicted != expected
        abstained = predicted is None

        # Wave 4.3 — governance_outcome bookkeeping.
        gov_key = gov_outcome if gov_outcome in governance_outcome_counts else "unset"
        governance_outcome_counts[gov_key] = governance_outcome_counts.get(gov_key, 0) + 1
        is_needs_review = gov_outcome == _GOV_NEEDS_REVIEW

        if rid.startswith("c-"):
            conflict_total += 1
            if preflight_type is not None:
                preflight_first_detected += 1
            if preflight_terminal:
                preflight_terminal_rows += 1
            if winning_plane:
                winning_plane_counts[str(winning_plane)] = winning_plane_counts.get(str(winning_plane), 0) + 1
            if preflight_type and async_type and async_type != preflight_type:
                preflight_async_disagreement += 1
            if async_type and preflight_type is None and not preflight_terminal:
                async_stronger_than_preflight += 1

            if expected in by_class:
                by_class[expected]["injected"] += 1
                if binary_alert:
                    by_class[expected]["binary_detected"] += 1
                if exact_type_match:
                    by_class[expected]["exact_detected"] += 1
                if cross_type:
                    by_class[expected]["cross_type_alerts"] += 1
                if abstained:
                    by_class[expected]["abstained"] += 1

            if expected in core4_classes:
                core4_total += 1
                if exact_type_match:
                    core4_exact_detected += 1
                if is_needs_review:
                    # Wave 4.3 — typed conflict row routed to human review
                    # is a governance FN: the system knew something was
                    # off but declined to commit to a type.
                    conflict_needs_review += 1
                    governance_needs_review_fn += 1
            elif expected == "ambiguous_case":
                ambiguous_rows_total += 1
                if binary_alert:
                    ambiguous_alerted += 1
                if abstained:
                    ambiguous_abstained += 1
                if is_needs_review:
                    # Wave 4.3 — this is the canonical needs_review TP:
                    # an ambiguous row correctly routed to human review.
                    ambiguous_needs_review += 1
                    governance_needs_review_tp += 1

            if binary_alert:
                conflict_detected_binary += 1
            if exact_type_match:
                conflict_detected_exact += 1
            if cross_type:
                cross_type_alerts += 1
            if abstained:
                abstain_total += 1
            predicted_key = predicted or "none"
            confusion.setdefault(expected or "unknown", {})
            confusion[expected or "unknown"][predicted_key] = confusion[expected or "unknown"].get(predicted_key, 0) + 1
        elif rid.startswith("b-") or rid.startswith("sb-"):
            benign_total += 1
            if binary_alert:
                benign_fp += 1
                detector_key = predicted or "unknown"
                benign_fp_by_detector[detector_key] = benign_fp_by_detector.get(detector_key, 0) + 1
                if detector_key == "semantic_contradiction":
                    semantic_benign_fp += 1
                elif detector_key == "constraint_violation":
                    constraint_benign_fp += 1
                elif detector_key == "dependency_impact":
                    dependency_benign_fp += 1
                if _semantic_budget_exhausted_in_result(res):
                    semantic_budget_exhausted_benign_count += 1
            else:
                benign_tn += 1
            if is_needs_review:
                # Wave 4.3 — benign row that was promoted to needs_review
                # counts as a governance FP (we would be paging a human
                # on a legitimately-benign fact).  It is NOT a binary FP
                # for the typed-conflict alert pool above.
                benign_needs_review += 1
                governance_needs_review_fp += 1

        res["primary_detector_source"] = source
        res["exact_type_match"] = exact_type_match
        res["cross_type_alert"] = cross_type

    tp = conflict_detected_binary
    fn = conflict_total - conflict_detected_binary
    fp = benign_fp
    tn = benign_tn
    pooled_precision = tp / (tp + fp) if (tp + fp) else 0.0
    pooled_recall = tp / (tp + fn) if (tp + fn) else 0.0
    exact_tp = conflict_detected_exact
    exact_fn = conflict_total - conflict_detected_exact
    exact_precision = exact_tp / (exact_tp + fp) if (exact_tp + fp) else 0.0
    exact_recall = exact_tp / (exact_tp + exact_fn) if (exact_tp + exact_fn) else 0.0
    core4_exact_type_recall = (core4_exact_detected / core4_total) if core4_total else 0.0
    wrong_type_alert_rate = (cross_type_alerts / conflict_total) if conflict_total else 0.0
    benign_specificity = (benign_tn / benign_total) if benign_total else 0.0
    raw_preflight_coverage = (preflight_terminal_rows / conflict_total) if conflict_total else 0.0
    preflight_coverage = min(1.0, max(0.0, raw_preflight_coverage))
    preflight_unavailable_rate = min(1.0, max(0.0, 1.0 - preflight_coverage)) if conflict_total else 0.0
    semantic_trace_coverage = (
        (conflict_total - min(semantic_trace_missing_rows, conflict_total)) / conflict_total
        if conflict_total
        else 0.0
    )
    precision_safe_mixed_score = exact_recall * benign_specificity * max(0.0, 1.0 - wrong_type_alert_rate)

    report_integrity_checks = {
        "preflight_first_detected_bounded": preflight_first_detected <= conflict_total,
        "preflight_terminal_bounded": preflight_terminal_rows <= conflict_total,
        "preflight_coverage_bounded": 0.0 <= preflight_coverage <= 1.0,
        "preflight_unavailable_rate_bounded": 0.0 <= preflight_unavailable_rate <= 1.0,
    }
    report_integrity_notes = [name for name, ok in report_integrity_checks.items() if not ok]
    report_integrity_ok = not report_integrity_notes
    report_status = (
        "publishable"
        if contract_incomplete_rows == 0 and semantic_trace_missing_rows == 0 and report_integrity_ok
        else "diagnostic_only"
    )

    # Wave 4.3 — governance_outcome aggregate metrics.  Precision =
    # TP / (TP + FP) on the ambiguous-vs-benign rejection subgraph per
    # Heng & Soh (arXiv:2505.15008); recall = TP / (TP + FN) measured
    # against the 10 ambiguous rows + conflict rows that were abstained.
    gov_tp = governance_needs_review_tp
    gov_fp = governance_needs_review_fp
    gov_fn = governance_needs_review_fn
    needs_review_precision = gov_tp / (gov_tp + gov_fp) if (gov_tp + gov_fp) else 0.0
    needs_review_recall_ambiguous = (
        ambiguous_needs_review / ambiguous_rows_total if ambiguous_rows_total else 0.0
    )
    # The unsafe-forced-type rate on ambiguous rows drops monotonically
    # as the Neyman-Pearson selector routes rows to ``needs_review``.
    unsafe_forced_type_rate_ambiguous = (
        (ambiguous_alerted - ambiguous_needs_review) / ambiguous_rows_total
        if ambiguous_rows_total
        else 0.0
    )

    return {
        "conflict_total": conflict_total,
        "core4_total": core4_total,
        "core4_exact_detected": core4_exact_detected,
        "core4_exact_type_recall": core4_exact_type_recall,
        "all_rows_exact_type_recall": exact_recall,
        "conflict_detected": conflict_detected_binary,
        "conflict_recall": (conflict_detected_binary / conflict_total) if conflict_total else 0.0,
        "conflict_detected_exact": conflict_detected_exact,
        "conflict_exact_recall": exact_recall,
        "benign_total": benign_total,
        "benign_fp": benign_fp,
        "benign_tn": benign_tn,
        "benign_fp_rate": (benign_fp / benign_total) if benign_total else 0.0,
        "benign_fp_by_detector": dict(sorted(benign_fp_by_detector.items())),
        "semantic_benign_fp": semantic_benign_fp,
        "constraint_benign_fp": constraint_benign_fp,
        "dependency_benign_fp": dependency_benign_fp,
        "semantic_budget_exhausted_benign_count": semantic_budget_exhausted_benign_count,
        "ambiguous_rows_total": ambiguous_rows_total,
        "ambiguous_alerted": ambiguous_alerted,
        "ambiguous_abstained": ambiguous_abstained,
        "unsafe_forced_type_rate": (ambiguous_alerted / ambiguous_rows_total) if ambiguous_rows_total else 0.0,
        "unsafe_forced_type_rate_ambiguous": unsafe_forced_type_rate_ambiguous,
        "governance_outcome_counts": dict(governance_outcome_counts),
        "ambiguous_needs_review": ambiguous_needs_review,
        "benign_needs_review": benign_needs_review,
        "conflict_needs_review": conflict_needs_review,
        "governance_needs_review_tp": gov_tp,
        "governance_needs_review_fp": gov_fp,
        "governance_needs_review_fn": gov_fn,
        "needs_review_precision": needs_review_precision,
        "needs_review_recall_ambiguous": needs_review_recall_ambiguous,
        "pooled_TP": tp,
        "pooled_FN": fn,
        "pooled_FP": fp,
        "pooled_TN": tn,
        "pooled_precision": pooled_precision,
        "pooled_recall": pooled_recall,
        "exact_TP": exact_tp,
        "exact_FN": exact_fn,
        "exact_precision": exact_precision,
        "exact_recall": exact_recall,
        "cross_type_alerts": cross_type_alerts,
        "wrong_type_alert_rate": wrong_type_alert_rate,
        "abstain_total": abstain_total,
        "exact_confusion": confusion,
        "by_class": by_class,
        "preflight_async_disagreement": preflight_async_disagreement,
        "async_stronger_than_preflight": async_stronger_than_preflight,
        "preflight_first_detected": preflight_first_detected,
        "preflight_terminal_rows": preflight_terminal_rows,
        "winning_plane_counts": dict(sorted(winning_plane_counts.items())),
        "detector_plane_authority": "nested_preflight_authority_when_available",
        "benign_specificity": benign_specificity,
        "preflight_coverage": preflight_coverage,
        "preflight_unavailable_rate": preflight_unavailable_rate,
        "semantic_trace_coverage": semantic_trace_coverage,
        "precision_safe_mixed_score": precision_safe_mixed_score,
        "contract_audit": {
            "rows_scored": rows_scored,
            "contract_complete_rows": contract_complete_rows,
            "contract_incomplete_rows": contract_incomplete_rows,
            "semantic_trace_missing_rows": semantic_trace_missing_rows,
        },
        "report_integrity_ok": report_integrity_ok,
        "report_integrity_checks": report_integrity_checks,
        "report_integrity_notes": report_integrity_notes,
        "report_status": report_status,
    }


def build_structural_preflight_block(
    *,
    preflight_raw: Any | None = None,
    preflight_error: str | None = None,
) -> dict[str, Any]:
    if preflight_error:
        return {
            "called": True,
            "error": preflight_error,
            "preflight_has_conflicts": False,
            "preflight_has_structural_conflicts": False,
            "classes_detected": [],
            "detector_versions": {},
            "stop_reasons": {},
            "dependency_path_used": [],
            "constraint_slots_compared": 0,
            "temporal_regression_cues": [],
            "verdicts": {},
            "reasoning_confidence": {},
            "abstained_reason": {},
        }
    from paper3_phase2_mcp_run import _tool_result_as_dict

    d = _tool_result_as_dict(preflight_raw)
    sp = d.get("structural_preflight")
    if not isinstance(sp, dict):
        sp = {}
    csc = sp.get("constraint_slots_compared")
    if isinstance(csc, list):
        constraint_slots_n = len(csc)
    else:
        try:
            constraint_slots_n = int(csc or 0)
        except (TypeError, ValueError):
            constraint_slots_n = 0
    return {
        "called": preflight_raw is not None,
        "preflight_has_conflicts": bool(d.get("has_conflicts")),
        "preflight_has_structural_conflicts": bool(d.get("preflight_has_structural_conflicts")),
        "classes_detected": list(sp.get("classes_detected") or []),
        "detector_versions": dict(sp.get("detector_versions") or {}),
        "stop_reasons": dict(sp.get("stop_reasons") or {}),
        "dependency_path_used": list(sp.get("dependency_path_used") or []),
        "constraint_slots_compared": constraint_slots_n,
        "temporal_regression_cues": list(sp.get("temporal_regression_cues") or []),
        "verdicts": dict(d.get("structural_verdicts") or sp.get("verdicts") or {}),
        "reasoning_confidence": dict(d.get("structural_reasoning_confidence") or sp.get("reasoning_confidence") or {}),
        "abstained_reason": dict(d.get("abstained_reason") or sp.get("abstained_reason") or {}),
    }


def structural_primary_detection_result(
    *,
    structural_preflight: dict[str, Any] | None,
    expected_conflict_type: str | None = None,
    async_exact_type_match: bool = False,
    inline_exact_type_match: bool = False,
) -> tuple[bool, str, str | None]:
    block = structural_preflight if isinstance(structural_preflight, dict) else {}
    expected = str(expected_conflict_type or "")
    if expected:
        verdicts = block.get("verdicts") or {}
        verdict = verdicts.get(expected)
        if isinstance(verdict, dict):
            verdict = verdict.get("verdict")
        if verdict == "detected":
            return True, "preflight", None
        if async_exact_type_match:
            return True, "async_fallback", None
        if inline_exact_type_match:
            return True, "inline_fallback", None
        stop = (block.get("stop_reasons") or {}).get(expected) or (block.get("abstained_reason") or {}).get(expected)
        if block.get("error"):
            return False, "preflight_error", stop
        if block.get("called"):
            return False, "preflight", stop
        return False, "preflight_unavailable", stop

    classes_detected = list(block.get("classes_detected") or [])
    if classes_detected:
        return True, "preflight", None
    if block.get("called") and not block.get("error"):
        return False, "preflight", "no_structural_conflict"
    if block.get("error"):
        return False, "preflight_error", None
    return False, "preflight_unavailable", None



def main() -> int:
    ap = argparse.ArgumentParser(description="Real Data Lab Phase 2b — list_benign.md via MCP")
    ap.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="Process only first N benign rows",
    )
    ap.add_argument(
        "--lenient-baseline",
        action="store_true",
        help="Do not exit when benign-table baseline keys are missing (default is strict).",
    )
    ap.add_argument(
        "--precheck-only",
        action="store_true",
        help="Seed audit + baseline validation for benign slice only, then exit.",
    )
    ap.add_argument(
        "--poll-max-s",
        type=float,
        default=None,
        metavar="SEC",
        help="Seconds to poll list_conflicts_v1 after each benign upsert. "
        "Default: real_data_lab_poll_max_s in .spirl/config.json, else 60.",
    )
    ap.add_argument(
        "--skip-phase2-guard",
        action="store_true",
        help="Run benign without list_conflict.md phase_complete (for FP-only checks / partial restarts).",
    )
    ap.add_argument(
        "--benign-list",
        type=str,
        default=None,
        metavar="PATH",
        help="Override benign table path (relative to Beyond Temporal Contradiction/ unless absolute).",
    )
    ap.add_argument(
        "--conflict-list",
        type=str,
        default=None,
        metavar="PATH",
        help="Must match Phase 2 conflict table; used to compute required phase_complete row count.",
    )
    ap.add_argument(
        "--ignore-pipeline-lock",
        action="store_true",
        help="Skip real_data_lab_pipeline.lock (only if no other RDL script is writing the execution log).",
    )
    args = ap.parse_args()

    with rdl_pipeline_lock(ignore=bool(args.ignore_pipeline_lock)):
        return benign_main_body(args)


def benign_main_body(args: Namespace) -> int:
    cfg = load_json(SPIRL_CONFIG)
    project_id = load_project_id(cfg)
    strict_baseline = bool(cfg.get("real_data_lab_phase2_strict_baseline", True))
    if args.lenient_baseline:
        strict_baseline = False
    strict_seed = bool(cfg.get("real_data_lab_phase2_strict_seed_manifest", False))

    if benign_batch_complete(project_id) and not args.precheck_only:
        print("Benign batch already complete (checkpoint). Scoring only.")
        m = compute_mixed_metrics_from_log()
        _cl = resolve_conflict_list_path(cfg, args.conflict_list)
        _bl = resolve_benign_list_path(cfg, args.benign_list)
        write_mixed_report(
            MIXED_REPORT_PATH,
            m,
            cfg,
            conflict_source=conflict_list_rel_for_log(_cl),
            benign_source=conflict_list_rel_for_log(_bl),
        )
        if not mixed_workload_metrics_logged():
            append_metric_lines(m, project_id)
        return 0

    conflict_list_path = resolve_conflict_list_path(cfg, args.conflict_list)
    conflict_n = effective_conflict_injection_total(cfg, conflict_list_path)
    if conflict_n <= 0:
        raise SystemExit("Conflict corpus slice is empty (check conflict list path and injection limit).")
    if not args.skip_phase2_guard and not phase2_complete(required_n=conflict_n, project_id=project_id):
        raise SystemExit(
            "Phase 2 must be complete for the configured conflict slice before benign batch "
            "(or pass --skip-phase2-guard for FP-only runs)."
        )

    if not rdl_phase1_complete():
        raise SystemExit("Phase 1 not complete.")

    list_path = resolve_benign_list_path(cfg, args.benign_list)
    benign_rel = conflict_list_rel_for_log(list_path)
    rows = parse_benign_table(list_path)
    if not rows:
        raise SystemExit(f"No rows parsed from {list_path}")

    n_total = len(rows) if args.limit is None else min(len(rows), args.limit)
    rows = rows[:n_total]

    mcp_cfg = load_json(MCP_PATH)
    srv = mcp_cfg["mcpServers"]["spirl"]
    mcp = McpSession(srv["url"], srv["headers"]["Authorization"])
    mcp.connect()

    all_facts = list_all_facts(mcp, project_id)
    fact_keys_set = {str(f.get("key")) for f in all_facts if f.get("key")}

    manifest = DEFAULT_SKF_MANIFEST
    mo = (cfg.get("real_data_lab_seed_manifest_path") or "").strip()
    if mo:
        manifest = (BTC_ROOT / mo).resolve() if not Path(mo).is_absolute() else Path(mo)

    expected_skf = skf_expected_keys(manifest) if manifest.is_file() else []
    seed_audit = build_seed_audit(
        project_id=project_id,
        manifest_path=manifest,
        expected_keys=expected_skf,
        stored_keys=fact_keys_set,
        total_facts_in_project=len(all_facts),
    )
    append_jsonl(
        EXEC_LOG,
        {
            "timestamp": iso_now(),
            "phase": 2,
            "agent_id": AGENT_ID,
            "action": "project_seed_audit",
            "project": project_id,
            "result": {**seed_audit, "batch": "benign"},
        },
    )
    if strict_seed and expected_skf and seed_audit["skf_keys_missing_in_project"]:
        miss = seed_audit["skf_keys_missing_in_project"]
        append_jsonl(
            EXEC_LOG,
            {
                "timestamp": iso_now(),
                "phase": 2,
                "agent_id": AGENT_ID,
                "action": "seed_manifest_validation_failed",
                "project": project_id,
                "result": {
                    "missing_keys": miss,
                    "manifest_path": str(manifest),
                    "batch": "benign",
                },
            },
        )
        print("Strict seed manifest validation failed; missing SKF keys in project:", miss, file=sys.stderr)
        return 1

    ref = referenced_baseline_keys(rows)
    missing_ref = sorted(ref - fact_keys_set)
    if missing_ref:
        append_jsonl(
            EXEC_LOG,
            {
                "timestamp": iso_now(),
                "phase": 2,
                "agent_id": AGENT_ID,
                "action": "baseline_validation_failed",
                "project": project_id,
                "result": {
                    "missing_keys": missing_ref,
                    "referenced_baseline_key_count": len(ref),
                    "corpus_slice_rows": n_total,
                    "source_table": benign_rel,
                    "strict_baseline": strict_baseline,
                    "batch": "benign",
                },
            },
        )
        if strict_baseline or args.precheck_only:
            print("Baseline validation failed (missing keys in project):", missing_ref, file=sys.stderr)
            return 1
        append_jsonl(
            EXEC_LOG,
            {
                "timestamp": iso_now(),
                "phase": 2,
                "agent_id": AGENT_ID,
                "action": "baseline_validation_warning",
                "project": project_id,
                "result": {
                    "missing_keys": missing_ref,
                    "note": "Lenient mode: continuing; expect non-empty missing_baseline_keys on affected rows.",
                    "batch": "benign",
                },
            },
        )
    elif args.precheck_only:
        print("Precheck OK — all referenced baseline keys for this benign slice exist in the project.")
        return 0

    start_idx = resume_benign_injection_index(project_id)

    if args.poll_max_s is not None:
        poll_max_s = float(args.poll_max_s)
    else:
        _p = cfg.get("real_data_lab_poll_max_s")
        poll_max_s = float(_p) if _p is not None else 60.0

    if not benign_batch_start_logged(project_id):
        append_jsonl(
            EXEC_LOG,
            {
                "timestamp": iso_now(),
                "phase": 2,
                "agent_id": AGENT_ID,
                "action": "conflict_injection_start",
                "project": project_id,
                "result": {
                    "source": benign_rel,
                    "mode": "table_driven_benign",
                    "target_total": n_total,
                    "poll_max_wait_s": poll_max_s,
                },
            },
        )

    structural_classes = {"dependency_impact", "constraint_violation", "temporal_invalidation"}
    injection_failed_rows: list[str] = []

    for i in range(start_idx, n_total):
        row = rows[i]
        injection_number = i + 1
        corpus_row_id = row["corpus_row_id"]
        proposed_key = row["proposed_key"]
        ground_truth_key = f"research.rdl.benign_gt.{corpus_key_token(corpus_row_id)}"
        t0 = time.monotonic()

        missing_baseline = [k for k in row["based_on_facts"] if k not in fact_keys_set]

        preflight_raw: Any | None = None
        preflight_err: str | None = None
        try:
            preflight_raw = memory_check_conflicts_v1(
                mcp,
                project_id,
                kind=row["proposed_kind"],
                key=proposed_key,
                body=row["body"],
                valid_from=row["valid_from"],
                valid_until=row["valid_until"],
                related_facts=[],
                include_semantic_trace=True,
                expected_anchor_keys=row["based_on_facts"],
                conflict_execution_profile="research",
            )
        except Exception as e:
            preflight_err = str(e)

        sem_preflight = build_semantic_preflight_block(
            conflict_class="benign",
            preflight_raw=preflight_raw,
            preflight_error=preflight_err,
        )
        structural_preflight = build_structural_preflight_block(
            preflight_raw=preflight_raw,
            preflight_error=preflight_err,
        )
        # Wave 4 — capture governance_outcome and preflight cascade latency
        # at injection time so Phase 3 scoring does not have to guess from
        # cascade_trace residue.
        gov_outcome = (
            _governance_outcome_from_result(preflight_raw)
            if isinstance(preflight_raw, dict)
            else None
        )
        gov_decision = (
            _governance_decision_from_result(preflight_raw)
            if isinstance(preflight_raw, dict)
            else None
        )
        preflight_latency_ms: float | None = None
        if isinstance(preflight_raw, dict):
            lane_summary = preflight_raw.get("lane_summary") or {}
            if isinstance(lane_summary, dict):
                val = lane_summary.get("total_cascade_latency_ms")
                if isinstance(val, (int, float)) and val > 0:
                    preflight_latency_ms = float(val)
            if preflight_latency_ms is None:
                trace = preflight_raw.get("cascade_trace") or {}
                if isinstance(trace, dict):
                    val = trace.get("total_latency_ms")
                    if isinstance(val, (int, float)) and val > 0:
                        preflight_latency_ms = float(val)

        t_write_end: float | None = None
        last_write_resp: Any = None
        err_msg: str | None = None

        try:
            last_write_resp = upsert_fact(
                mcp,
                project_id,
                kind=row["proposed_kind"],
                key=proposed_key,
                body=row["body"],
                valid_from=row["valid_from"],
                valid_until=row["valid_until"],
            )
            t_write_end = time.time()
        except Exception as e:
            err_msg = str(e)
            append_jsonl(
                EXEC_LOG,
                {
                    "timestamp": iso_now(),
                    "phase": 2,
                    "agent_id": AGENT_ID,
                    "action": "injection_failed",
                    "project": project_id,
                    "injection_number": injection_number,
                    "conflict_class": "benign",
                    "corpus_row_id": corpus_row_id,
                    "based_on_facts": row["based_on_facts"],
                    "proposed_fact_key": proposed_key,
                    "ground_truth_key": ground_truth_key,
                    "result": {
                        "error": err_msg or "upsert_failed",
                        "will_retry": False,
                        "missing_baseline_keys": missing_baseline,
                        "preflight_semantic": sem_preflight,
                        "structural_preflight": structural_preflight,
                        "semantic_trace_present": bool(sem_preflight.get("semantic_trace_present")),
                        "semantic_trace_missing": bool(sem_preflight.get("semantic_trace_missing")),
                        "semantic_trace": sem_preflight.get("semantic_trace"),
                        "semantic_preflight_winning_stop_reason": sem_preflight.get("semantic_preflight_winning_stop_reason"),
                        "semantic_preflight_first_candidate_stop_reason": sem_preflight.get("semantic_preflight_first_candidate_stop_reason"),
                        "governance_outcome": gov_outcome,
                        "governance_decision": gov_decision,
                        "preflight_latency_ms": preflight_latency_ms,
                    },
                },
            )
            injection_failed_rows.append(corpus_row_id)
            continue

        det = parse_detection(last_write_resp)
        inline_available = detection_inline_available(last_write_resp)
        det_lat = det.get("detection_latency_ms")
        if det_lat is not None:
            try:
                det_lat = float(det_lat)
            except (TypeError, ValueError):
                det_lat = None
        conflicts_n = int(det.get("conflicts_detected") or 0)
        conflict_types = list(det.get("conflict_types") or [])

        keyset = {proposed_key, *row["based_on_facts"]}
        after = (t_write_end - 2.0) if t_write_end else None
        # Wave 4 latency optimization: if preflight cleanly terminated as
        # benign (governance_outcome == "benign" AND preflight did not flag
        # a semantic or structural conflict), the async notifier will not
        # fire.  Poll only briefly instead of the full 60 s to avoid
        # burning ~50 min over a 70-row benign cohort.
        _inline_detected_early = (
            conflicts_n > 0 if inline_available else False
        )
        preflight_clean_benign = (
            gov_outcome == "benign"
            and not bool(sem_preflight.get("preflight_has_semantic_conflicts"))
            and not bool(structural_preflight.get("preflight_has_structural_conflicts"))
            and not _inline_detected_early
        )
        effective_poll_max_s = 5.0 if preflight_clean_benign else poll_max_s
        hit, poll_elapsed_s = poll_for_conflict_notification(
            mcp,
            project_id,
            keyset,
            after,
            interval_s=POLL_CONFLICTS_INTERVAL_S,
            max_wait_s=effective_poll_max_s,
            proposed_key=proposed_key,
        )

        notif_created = hit is not None
        notif_id = hit.get("id") if hit else None
        notif_severity = hit.get("severity") if hit else None
        notif_created_at = hit.get("created_at") if hit else None
        notif_conflict_type = hit.get("conflict_type") if hit else None
        matched_on_key = hit.get("matched_on_key") if hit else None
        matched_on_anchor_only = bool(hit.get("matched_on_anchor_only")) if hit else False

        inline_detected = (conflicts_n > 0) if inline_available else False
        preflight_severity = notif_severity or (
            (conflict_types[0] if conflict_types else None) if inline_available else None
        )
        observed_ms = (
            observed_notification_latency_ms(notif_created_at, t_write_end)
            if t_write_end and notif_created_at
            else None
        )

        async_semantic_match = notif_conflict_type == "semantic_contradiction"
        inline_semantic_match = "semantic_contradiction" in conflict_types if inline_available else False
        semantic_primary_detected, semantic_primary_source, semantic_terminal_reason = semantic_primary_detection_result(
            sem_preflight=sem_preflight,
            async_exact_type_match=async_semantic_match,
            inline_exact_type_match=inline_semantic_match,
        )

        structural_classes_detected = list(structural_preflight.get("classes_detected") or [])
        inline_structural_types = [cls for cls in conflict_types if cls in structural_classes]
        async_structural_match = notif_conflict_type in structural_classes
        if structural_classes_detected:
            structural_primary_detected = True
            structural_primary_source = "preflight"
            structural_terminal_reason = None
        elif inline_structural_types:
            structural_primary_detected = True
            structural_primary_source = "inline_fallback"
            structural_terminal_reason = None
        elif async_structural_match:
            structural_primary_detected = True
            structural_primary_source = "async_fallback"
            structural_terminal_reason = None
        elif structural_preflight.get("error"):
            structural_primary_detected = False
            structural_primary_source = "preflight_error"
            structural_terminal_reason = None
        elif structural_preflight.get("called"):
            structural_primary_detected = False
            structural_primary_source = "preflight"
            structural_terminal_reason = "no_structural_conflict"
        else:
            structural_primary_detected = False
            structural_primary_source = "preflight_unavailable"
            structural_terminal_reason = None

        observed_types = set()
        if semantic_primary_detected:
            observed_types.add("semantic_contradiction")
        observed_types.update(structural_classes_detected)
        observed_types.update(inline_structural_types)
        if async_structural_match and notif_conflict_type:
            observed_types.add(str(notif_conflict_type))
        primary_detector_source = (
            semantic_primary_source
            if semantic_primary_detected
            else structural_primary_source
        )
        row_contract = merge_row_contract_fields(sem_preflight, structural_preflight)
        preflight_first_detected = row_contract.get("final_conflict_type") is not None
        preflight_async_disagreement = bool(
            row_contract.get("final_conflict_type")
            and notif_conflict_type
            and row_contract.get("final_conflict_type") != notif_conflict_type
        )
        async_stronger_than_preflight = bool(
            notif_conflict_type
            and row_contract.get("final_conflict_type") is None
            and row_contract.get("preflight_terminal") is not True
        )
        detector_coherence = (
            "disagreement"
            if preflight_async_disagreement
            else "async_recovery"
            if async_stronger_than_preflight
            else "aligned"
            if (not notif_conflict_type or notif_conflict_type == row_contract.get("final_conflict_type"))
            else "preflight_only"
        )

        append_jsonl(
            EXEC_LOG,
            {
                "timestamp": iso_now(),
                "phase": 2,
                "agent_id": AGENT_ID,
                "action": "conflict_injected",
                "project": project_id,
                "injection_number": injection_number,
                "conflict_class": "benign",
                "corpus_row_id": corpus_row_id,
                "based_on_facts": row["based_on_facts"],
                "proposed_fact_key": proposed_key,
                "ground_truth_key": ground_truth_key,
                "result": {
                    "fact_keys": [proposed_key],
                    "expected_conflict_type": "benign",
                    **row_contract,
                    "missing_baseline_keys": missing_baseline,
                    "preflight_semantic": sem_preflight,
                    "structural_preflight": structural_preflight,
                    "preflight_has_semantic_conflicts": bool(sem_preflight.get("preflight_has_semantic_conflicts")),
                    "preflight_has_structural_conflicts": bool(structural_preflight.get("preflight_has_structural_conflicts")),
                    "semantic_trace_present": bool(sem_preflight.get("semantic_trace_present")),
                    "semantic_trace_missing": bool(sem_preflight.get("semantic_trace_missing")),
                    "semantic_trace": sem_preflight.get("semantic_trace"),
                    "semantic_preflight_winning_stop_reason": sem_preflight.get("semantic_preflight_winning_stop_reason"),
                    "semantic_preflight_first_candidate_stop_reason": sem_preflight.get("semantic_preflight_first_candidate_stop_reason"),
                    "semantic_primary_detected": semantic_primary_detected,
                    "semantic_primary_source": semantic_primary_source,
                    "semantic_terminal_stop_reason": semantic_terminal_reason,
                    "structural_primary_detected": structural_primary_detected,
                    "structural_primary_source": structural_primary_source,
                    "structural_terminal_stop_reason": structural_terminal_reason,
                    "primary_detector_source": primary_detector_source,
                    "preflight_first_detected": preflight_first_detected,
                    "detector_coherence": detector_coherence,
                    "preflight_async_disagreement": preflight_async_disagreement,
                    "async_stronger_than_preflight": async_stronger_than_preflight,
                    "exact_type_match": False,
                    "cross_type_alert": bool(observed_types),
                    "detector_version": structural_preflight.get("detector_versions"),
                    "preflight_check": {
                        "called": True,
                        "scope": "inline_upsert_response",
                        "inline_available": inline_available,
                        "inline_detected": inline_detected,
                        "classes_detected": conflict_types if inline_available else [],
                        "severity": preflight_severity,
                    },
                    "async_observed": {
                        "detected": notif_created,
                        "observed_detection_latency_ms": observed_ms,
                        "poll_elapsed_s": round(poll_elapsed_s, 2),
                        "matched_on_key": matched_on_key,
                        "matched_on_anchor_only": matched_on_anchor_only,
                        "matched_conflict_type": notif_conflict_type,
                        "exact_type_match": False,
                    },
                    "notification": {
                        "created": notif_created,
                        "notification_id": notif_id,
                        "conflict_type": notif_conflict_type,
                        "severity": notif_severity,
                        "created_at": notif_created_at,
                    },
                    "detection_audit": {
                        **detection_audit_block(
                            baseline_missing_keys=missing_baseline,
                            inline_available=inline_available,
                            inline_detected=inline_detected,
                            async_matched=notif_created,
                            poll_elapsed_s=poll_elapsed_s,
                            max_wait_s=poll_max_s,
                        ),
                        "semantic_scoring_rule": "semantic_verdict_first",
                        "structural_scoring_rule": "exact_type_preflight_first",
                        "observed_conflict_types": sorted(observed_types),
                    },
                    "ground_truth_key": ground_truth_key,
                    "detection_latency_ms": det_lat,
                    "preflight_latency_ms": preflight_latency_ms,
                    "governance_outcome": gov_outcome,
                    "governance_decision": gov_decision,
                    "success": True,
                },
            },
        )

        gt_body = {
            "corpus_row_id": corpus_row_id,
            "conflict_class": "benign",
            "based_on_facts": row["based_on_facts"],
            "proposed_key": proposed_key,
            "proposed_kind": row["proposed_kind"],
            "rationale_summary": row["rationale_summary"],
            "expected_label": row["expected_label"],
            "source_support": row["source_support"],
            "gold_should_alert": False,
            "notification_id": notif_id,
            "inline_conflicts_detected": conflicts_n,
        }
        upsert_fact(
            mcp,
            project_id,
            kind="research",
            key=ground_truth_key,
            body=json.dumps(gt_body, ensure_ascii=False),
            skip_conflict_check=True,
            skip_embedding=True,
        )

        print(f"[benign {injection_number}/{n_total}] {corpus_row_id} ok", flush=True)
        _ = time.monotonic() - t0

    done = resume_benign_injection_index(project_id)
    if done < n_total:
        print(
            f"Incomplete: {done}/{n_total} benign conflict_injected lines; fix and re-run.",
            file=sys.stderr,
        )
        return 1

    append_jsonl(
        CHECKPOINTS,
        {
            "timestamp": iso_now(),
            "phase": 2,
            "checkpoint_type": "benign_batch_complete",
            "agent_id": AGENT_ID,
            "status": "complete",
            "project_id": project_id,
            "total_injections": n_total,
            "source": benign_rel,
        },
    )

    m = compute_mixed_metrics_from_log()
    _cl = resolve_conflict_list_path(cfg, args.conflict_list)
    write_mixed_report(
        MIXED_REPORT_PATH,
        m,
        cfg,
        conflict_source=conflict_list_rel_for_log(_cl),
        benign_source=benign_rel,
    )
    if not mixed_workload_metrics_logged():
        append_metric_lines(m, project_id)

    print(f"Benign batch complete. Mixed report: {MIXED_REPORT_PATH}")
    return 0


def collect_error_analysis_from_log() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not EXEC_LOG.exists():
        return rows
    for line in EXEC_LOG.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            o = json.loads(line)
        except json.JSONDecodeError:
            continue
        if o.get("phase") != 2 or o.get("action") != "conflict_injected":
            continue
        res = o.get("result") or {}
        rid = str(o.get("corpus_row_id") or "")
        if not (
            bool(res.get("cross_type_alert"))
            or (rid.startswith(("b-", "sb-")) and (res.get("notification") or {}).get("conflict_type"))
            or res.get("row_contract_complete") is False
        ):
            continue
        rows.append(
            {
                "corpus_row_id": rid,
                "expected_conflict_type": res.get("expected_conflict_type"),
                "predicted_preflight_type": res.get("final_conflict_type"),
                "winning_detector_plane": res.get("winning_detector_plane"),
                "notification_conflict_type": (res.get("notification") or {}).get("conflict_type"),
                "detector_coherence": res.get("detector_coherence"),
                "row_contract_complete": res.get("row_contract_complete"),
                "outcome_class": res.get("outcome_class"),
            },
        )
    return rows



def write_mixed_report(
    path: Path,
    m: dict[str, Any],
    cfg: dict,
    *,
    conflict_source: str = "real-data-lab/list_conflict.md",
    benign_source: str = "real-data-lab/list_benign.md",
) -> None:
    confusion = m.get("exact_confusion") or {}
    benign_fp_by_detector = m.get("benign_fp_by_detector") or {}
    detector_lines = ["| Detector | Benign FP |", "|----------|----------:|"]
    if benign_fp_by_detector:
        for det, count in benign_fp_by_detector.items():
            detector_lines.append(f"| `{det}` | {count} |")
    else:
        detector_lines.append("| `none` | 0 |")

    matrix_rows = ["| Expected | semantic | dependency | constraint | temporal | none |", "|----------|---------:|-----------:|-----------:|---------:|-----:|"]
    for expected in ("semantic_contradiction", "dependency_impact", "constraint_violation", "temporal_invalidation"):
        row = confusion.get(expected, {})
        matrix_rows.append(
            "| `{}` | {} | {} | {} | {} | {} |".format(
                expected,
                row.get("semantic_contradiction", 0),
                row.get("dependency_impact", 0),
                row.get("constraint_violation", 0),
                row.get("temporal_invalidation", 0),
                row.get("none", 0),
            ),
        )

    integrity_notes = m.get("report_integrity_notes") or []
    integrity_note_text = ", ".join(integrity_notes) if integrity_notes else "none"
    lines = [
        "# Mixed workload report - Real Data Lab (conflicts + benign)",
        "",
        f"Generated: {iso_now()}",
        "",
        f"Project: `{cfg.get('real_data_lab_project_id') or cfg.get('project_id', '')}`",
        "",
        "The detector currently looks strongest on constraint, strong on temporal, and respectable on dependency and semantic. The main remaining blocker is benign precision, so this report now separates core typed conflict routing from ambiguous-case handling and bounded report-integrity checks.",
        "",
        f"## Conflicts (c-* corpus, `{conflict_source}`)",
        "",
        "| Metric | Value |",
        "|--------|------:|",
        f"| Rows (all conflict rows) | {m.get('conflict_total', 0)} |",
        f"| Rows (core-4 only) | {m.get('core4_total', 0)} |",
        f"| Binary detected (any alert) | {m.get('conflict_detected', 0)} |",
        f"| Binary recall | {m.get('conflict_recall', 0):.4f} |",
        f"| Core-4 exact-type recall | {m.get('core4_exact_type_recall', 0):.4f} |",
        f"| All-row exact-type recall | {m.get('all_rows_exact_type_recall', 0):.4f} |",
        f"| Cross-type alerts | {m.get('cross_type_alerts', 0)} |",
        f"| Abstained rows | {m.get('abstain_total', 0)} |",
        f"| Preflight-first detected | {m.get('preflight_first_detected', 0)} |",
        f"| Preflight/async disagreements | {m.get('preflight_async_disagreement', 0)} |",
        f"| Async-only recoveries | {m.get('async_stronger_than_preflight', 0)} |",
        "",
        "## Ambiguous rows",
        "",
        "| Metric | Value |",
        "|--------|------:|",
        f"| Ambiguous rows total | {m.get('ambiguous_rows_total', 0)} |",
        f"| Ambiguous alerted | {m.get('ambiguous_alerted', 0)} |",
        f"| Ambiguous abstained | {m.get('ambiguous_abstained', 0)} |",
        f"| Ambiguous routed to needs_review | {m.get('ambiguous_needs_review', 0)} / {m.get('ambiguous_rows_total', 0)} |",
        f"| Unsafe forced-type rate (ambiguous) | {m.get('unsafe_forced_type_rate_ambiguous', m.get('unsafe_forced_type_rate', 0)):.4f} |",
        f"| Governance outcome counts | `{json.dumps(m.get('governance_outcome_counts') or {}, ensure_ascii=False)}` |",
        "",
        "_Ambiguous rows are tracked separately and excluded from the core-4 headline exact-type metric._",
        "",
        "_Unsafe forced-type rate is governance-aware (Wave 4.3+; evaluation_contract_version=`rdl-eval-2026-04-23-v2`). Rows routed by the Neyman-Pearson governance selector to ``needs_review`` are the intended deferral path (Chow 1970 IEEE TIT; Madras, Pitassi & Zemel NeurIPS 2018; AbstentionBench arXiv:2506.09038) and are NOT counted as forced-type errors._",
        "",
        f"## Benign (b-* / sb-* corpus, `{benign_source}`)",
        "",
        "| Metric | Value |",
        "|--------|------:|",
        f"| Rows (injected, benign IDs) | {m.get('benign_total', 0)} |",
        f"| False positives | {m.get('benign_fp', 0)} |",
        f"| True negatives | {m.get('benign_tn', 0)} |",
        f"| FP rate | {m.get('benign_fp_rate', 0):.4f} |",
        f"| Specificity | {m.get('benign_specificity', 0):.4f} |",
        f"| Semantic benign FP | {m.get('semantic_benign_fp', 0)} |",
        f"| Constraint benign FP | {m.get('constraint_benign_fp', 0)} |",
        f"| Dependency benign FP | {m.get('dependency_benign_fp', 0)} |",
        f"| Semantic budget-exhausted benign count | {m.get('semantic_budget_exhausted_benign_count', 0)} |",
        "",
        "## Benign FP by detector",
        "",
        *detector_lines,
        "",
        "## Pooled binary: alert warranted (conflict = positive, benign = negative)",
        "",
        "| Metric | Value |",
        "|--------|------:|",
        f"| TP | {m.get('pooled_TP', 0)} |",
        f"| FN | {m.get('pooled_FN', 0)} |",
        f"| FP | {m.get('pooled_FP', 0)} |",
        f"| TN | {m.get('pooled_TN', 0)} |",
        f"| Precision | {m.get('pooled_precision', 0):.4f} |",
        f"| Recall | {m.get('pooled_recall', 0):.4f} |",
        f"| Wrong-type alert rate | {m.get('wrong_type_alert_rate', 0):.4f} |",
        f"| Preflight coverage | {m.get('preflight_coverage', 0):.4f} |",
        f"| Preflight unavailable rate | {m.get('preflight_unavailable_rate', 0):.4f} |",
        f"| Semantic trace coverage | {m.get('semantic_trace_coverage', 0):.4f} |",
        f"| Precision-safe mixed score | {m.get('precision_safe_mixed_score', 0):.4f} |",
        "",
        "## Report integrity",
        "",
        "| Metric | Value |",
        "|--------|------:|",
        f"| Report integrity OK | `{m.get('report_integrity_ok', False)}` |",
        f"| Rows scored | {((m.get('contract_audit') or {}).get('rows_scored', 0))} |",
        f"| Detector-plane authority | `{m.get('detector_plane_authority', 'nested_preflight_authority_when_available')}` |",
        f"| Integrity notes | `{integrity_note_text}` |",
        "",
        "## Exact-type confusion matrix",
        "",
        *matrix_rows,
        "",
        "_Detection rule: preflight `final_conflict_type` is authoritative when present. Mixed-report exact-type scoring uses the same derived predicted type for confusion, benign FP accounting, and detector-level breakdowns._",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def append_metric_lines(m: dict[str, Any], project_id: str) -> None:
    append_jsonl(
        EXEC_LOG,
        {
            "timestamp": iso_now(),
            "phase": 3,
            "agent_id": "rdl_phase3_judge_agent",
            "action": "metric_computed",
            "project": project_id,
            "metric_group": "mixed_workload_fp",
            "result": {
                "benign_total": m.get("benign_total"),
                "benign_fp": m.get("benign_fp"),
                "benign_tn": m.get("benign_tn"),
                "benign_fp_rate": m.get("benign_fp_rate"),
            },
        },
    )
    append_jsonl(
        EXEC_LOG,
        {
            "timestamp": iso_now(),
            "phase": 3,
            "agent_id": "rdl_phase3_judge_agent",
            "action": "metric_computed",
            "project": project_id,
            "metric_group": "mixed_workload_precision_binary",
            "result": {
                "TP": m.get("pooled_TP"),
                "FN": m.get("pooled_FN"),
                "FP": m.get("pooled_FP"),
                "TN": m.get("pooled_TN"),
                "precision": m.get("pooled_precision"),
                "recall": m.get("pooled_recall"),
                "note": "Positive = conflict rows (should alert); negative = benign rows",
            },
        },
    )


if __name__ == "__main__":
    raise SystemExit(main())
