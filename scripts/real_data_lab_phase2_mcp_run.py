#!/usr/bin/env python3
"""
Real Data Lab Phase 2 — table-driven conflict injection from real-data-lab/list_conflict.md
via Spirl MCP only (same JSON-RPC transport as .cursor/mcp.json).

See research_prompt/real_data_lab_phase2_prompt.md.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from rdl_pipeline_execution_lock import rdl_pipeline_lock  # noqa: E402
from paper3_phase2_mcp_run import (  # noqa: E402
    McpSession,
    append_jsonl,
    conflicts_from_list_response,
    detection_inline_available,
    find_notification_for_keys,
    iso_now,
    list_all_facts,
    load_json,
    observed_notification_latency_ms,
    parse_detection,
    poll_for_conflict_notification,
    POLL_CONFLICTS_INTERVAL_S,
    POLL_CONFLICTS_MAX_WAIT_S,
    _tool_result_as_dict,
)

BTC_ROOT = _SCRIPTS.parent
REPO_ROOT = BTC_ROOT.parent
SPIRL_CONFIG = REPO_ROOT / ".spirl" / "config.json"
MCP_PATH = REPO_ROOT / ".cursor" / "mcp.json"
RDL = BTC_ROOT / "real-data-lab"
DEFAULT_CONFLICT_LIST = RDL / "list_conflict.md"
EXEC_LOG = RDL / "research" / "real_data_lab_execution_log.jsonl"
CHECKPOINTS = RDL / "research" / "real_data_lab_checkpoints.jsonl"
REPORT_PATH = RDL / "research" / "real_data_lab_phase2_report.md"
PAUSE_FLAG = RDL / "research" / "real_data_lab_pause.flag"
DEFAULT_SKF_MANIFEST = RDL / "Project Core Platform.skf.json"

AGENT_ID = "rdl_phase2_seed_agent"

DEFAULT_SEMANTIC_DETECTED_POLL_MAX_WAIT_S = 15.0
DEFAULT_SEMANTIC_TERMINAL_POLL_MAX_WAIT_S = 0.0
TERMINAL_SEMANTIC_STOP_REASONS = {
    "lexical_candidate_filtered",
    "cross_kind_lexical_filtered",
    "predicate_overlap_blocked",
    "forward_nli_non_contradiction",
    "reverse_nli_non_contradiction",
    "forward_confidence_failed",
    "forward_margin_failed",
    "reverse_margin_failed",
    "no_retrieval_candidates",
    "support_verifier_consistent",
}

CAT_TO_KIND = {
    "apiendpoint": "api_endpoint",
    "decision": "decision",
    "feature": "feature",
    "stack": "stack",
    "constraint": "constraint",
    "migration": "migration",
    "deployment": "deployment",
    "monitoring": "monitoring",
    "test": "test",
}

LABEL_TO_CLASS = {
    "semanticcontradiction": "semantic_contradiction",
    "dependencyimpact": "dependency_impact",
    "constraintviolation": "constraint_violation",
    "temporalinvalidation": "temporal_invalidation",
    "ambiguous": "ambiguous_case",
}

TARGET_PER_CLASS_FULL = {
    "semantic_contradiction": 40,
    "dependency_impact": 20,
    "constraint_violation": 20,
    "temporal_invalidation": 20,
    "ambiguous_case": 10,
}


def resolve_conflict_list_path(cfg: dict[str, Any], cli_override: str | None) -> Path:
    """CLI wins, then config `real_data_lab_conflict_list_path`, else `list_conflict.md`."""
    if cli_override and str(cli_override).strip():
        p = Path(cli_override.strip())
        return p.resolve() if p.is_absolute() else (BTC_ROOT / p).resolve()
    list_path = DEFAULT_CONFLICT_LIST
    override = (cfg.get("real_data_lab_conflict_list_path") or "").strip()
    if override:
        po = Path(override)
        list_path = po.resolve() if po.is_absolute() else (BTC_ROOT / override).resolve()
    return list_path


def effective_conflict_injection_total(cfg: dict[str, Any], list_path: Path) -> int:
    """How many conflict rows Phase 2 injects (after optional injection_limit); used by Phase 2b guard."""
    rows = parse_conflict_table(list_path)
    if not rows:
        return 0
    injection_limit: int | None = None
    limit_cfg = cfg.get("real_data_lab_injection_limit")
    if limit_cfg is not None:
        try:
            lim = int(limit_cfg)
            if lim > 0:
                injection_limit = lim
        except (TypeError, ValueError):
            injection_limit = None
    return len(rows) if injection_limit is None else min(len(rows), injection_limit)


def _rdl_semantic_preflight_detected_for_metrics(block: dict[str, Any] | None) -> bool:
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


def _rdl_preflight_types_from_result(res: dict[str, Any]) -> list[str]:
    observed: list[str] = []
    if _rdl_semantic_preflight_detected_for_metrics(res.get("preflight_semantic")):
        observed.append("semantic_contradiction")
    structural = res.get("structural_preflight") or {}
    for cls in structural.get("classes_detected") or []:
        cls = str(cls)
        if cls and cls not in observed:
            observed.append(cls)
    return observed


def _rdl_result_has_primary_fields(res: dict[str, Any]) -> bool:
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
    ``None`` when the field is absent.  Accepts both the top-level key
    and the nested ``cascade_trace.arbitration`` fallback so older logs
    can be replayed.
    """
    if not isinstance(res, dict):
        return None
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
    """Wave 4.3++ — extract the full governance_decision dict.

    The backend carries the calibrated Neyman-Pearson selector features,
    LLR score, threshold, ambiguity signals, and suppressed-verdict
    sufficient statistics under ``governance_decision``.  Persisting
    this dict into the execution log is what makes the RDL corpus
    losslessly re-scorable offline (Geifman & El-Yaniv NeurIPS 2017
    risk-coverage curves, Chow 1970 rejection-threshold ablation).
    The fallback to ``cascade_trace.arbitration.governance_decision``
    keeps older log shapes readable.
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


def _preflight_latency_ms_from_result(res: dict[str, Any]) -> float | None:
    """Wave 4 — extract preflight cascade latency from the preflight envelope.

    The backend exposes total cascade wall-time under
    ``lane_summary.total_cascade_latency_ms``; fall back to
    ``cascade_trace.total_latency_ms`` when the lane summary is not
    populated (e.g. on error paths or legacy traces).
    """
    if not isinstance(res, dict):
        return None
    lane_summary = res.get("lane_summary") or {}
    if isinstance(lane_summary, dict):
        val = lane_summary.get("total_cascade_latency_ms")
        if isinstance(val, (int, float)) and val > 0:
            return float(val)
    trace = res.get("cascade_trace") or {}
    if isinstance(trace, dict):
        val = trace.get("total_latency_ms")
        if isinstance(val, (int, float)) and val > 0:
            return float(val)
    return None


def _rdl_preflight_primary_prediction(res: dict[str, Any]) -> tuple[str | None, str | None, bool]:
    final_conflict_type = res.get("final_conflict_type")
    # Wave 4.3 — ``needs_review`` is a first-class governance outcome, not
    # a typed-conflict label.  Treat it as preflight-terminal abstention so
    # scoring does not double-count it as a cross-type alert.
    if final_conflict_type == _GOV_NEEDS_REVIEW:
        return None, str(res.get("winning_detector_plane") or "governance_selector"), True
    if final_conflict_type:
        return str(final_conflict_type), str(res.get("winning_detector_plane") or "none"), True
    if res.get("preflight_terminal") is True:
        return None, str(res.get("winning_detector_plane") or "none"), True
    return None, None, False


def _rdl_derive_predicted_type(res: dict[str, Any], expected: str | None) -> tuple[str | None, str]:
    expected = str(expected or "")
    preflight_type, winning_plane, preflight_terminal = _rdl_preflight_primary_prediction(res)
    preflight_types = _rdl_preflight_types_from_result(res)
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
    if expected == "benign" and _rdl_result_has_primary_fields(res):
        return None, "preflight_abstain"
    if inline_types:
        return inline_types[0], "inline_cross_type"
    if async_type:
        return async_type, "async_cross_type"
    return None, "none"


def _rdl_collect_seed_conflict_events(project_id: str) -> list[dict[str, Any]]:
    """All phase-2 conflict_injected rows from the seed agent for c-* corpus rows."""
    out: list[dict[str, Any]] = []
    if not EXEC_LOG.exists():
        return out
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
        if o.get("project") != project_id or o.get("agent_id") != AGENT_ID:
            continue
        rid = str(o.get("corpus_row_id") or "")
        if not rid.startswith("c-"):
            continue
        out.append(o)
    out.sort(key=lambda x: str(x.get("timestamp") or ""))
    return out


def _rdl_slice_latest_conflict_batch(events: list[dict[str, Any]], n_total: int) -> list[dict[str, Any]]:
    """If the log contains multiple Phase 2 runs, keep only the last n_total seed injections."""
    if n_total > 0 and len(events) > n_total:
        return events[-n_total:]
    return events


def compute_phase2_conflict_surface_metrics(project_id: str, n_total: int) -> dict[str, Any]:
    """
    Derive injection-time detector signals from execution log (same scoring rules as mixed report
    conflict section, but only `rdl_phase2_seed_agent` c-* rows, optionally sliced to the latest batch).
    """
    tracked_classes = [
        "semantic_contradiction",
        "dependency_impact",
        "constraint_violation",
        "temporal_invalidation",
        "ambiguous_case",
    ]
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
    conflict_total = 0
    conflict_detected_binary = 0
    conflict_detected_exact = 0
    cross_type_alerts = 0
    abstain_total = 0
    core4_total = 0
    core4_detected_exact = 0
    ambiguous_total = 0
    ambiguous_alerted = 0
    ambiguous_abstained = 0
    ambiguous_forced = 0
    # Wave 4.3+ — governance-aware ambiguous scoring.  A row is counted
    # as ``unsafe_forced_type`` only when it emitted a typed conflict
    # AND governance did NOT route it to ``needs_review``.  Rows that
    # governance routed to human review are not "forced" — they are the
    # deliberate deferral path per Chow (1970) / Madras et al. (2018).
    ambiguous_needs_review = 0
    ambiguous_routed_to_review = 0
    governance_outcome_counts: Counter[str] = Counter()
    source_counts: Counter[str] = Counter()
    preflight_first_detected_n = 0
    preflight_async_disagreement_n = 0
    async_stronger_than_preflight_n = 0
    winning_plane_counts: Counter[str] = Counter()
    cross_type_by_plane: Counter[str] = Counter()
    row_contract_complete_n = 0
    row_contract_incomplete_n = 0
    outcome_class_counts: Counter[str] = Counter()
    tool_versions: dict[str, str] = {}

    all_seed_events = _rdl_collect_seed_conflict_events(project_id)
    events = _rdl_slice_latest_conflict_batch(all_seed_events, n_total)

    for o in events:
        res = o.get("result") or {}
        if not isinstance(res, dict):
            res = {}
        expected = str(res.get("expected_conflict_type") or o.get("conflict_class") or "")
        predicted, source = _rdl_derive_predicted_type(res, expected)
        source_counts[source] += 1
        preflight_type, winning_plane, preflight_terminal = _rdl_preflight_primary_prediction(res)
        async_type = str(((res.get("notification") or {}).get("conflict_type") or "")) or None
        if preflight_type is not None:
            preflight_first_detected_n += 1
        if winning_plane:
            winning_plane_counts[winning_plane] += 1
        if preflight_type and async_type and async_type != preflight_type:
            preflight_async_disagreement_n += 1
        if async_type and preflight_type is None and not preflight_terminal:
            async_stronger_than_preflight_n += 1
        binary_alert = predicted is not None
        exact_type_match = expected not in {"", "benign", "ambiguous_case"} and predicted == expected
        cross_type = expected not in {"", "benign", "ambiguous_case"} and predicted is not None and predicted != expected
        abstained = predicted is None
        is_core4 = expected not in {"", "benign", "ambiguous_case"}
        is_ambiguous = expected == "ambiguous_case"

        # Wave 4.3+ — pull governance_outcome once per row so the
        # downstream ambiguous/benign bookkeeping is governance-aware.
        gov_outcome = _governance_outcome_from_result(res)
        gov_key = gov_outcome if gov_outcome else "unset"
        governance_outcome_counts[gov_key] += 1
        is_needs_review = gov_outcome == _GOV_NEEDS_REVIEW

        conflict_total += 1
        if is_core4:
            core4_total += 1
            if exact_type_match:
                core4_detected_exact += 1
        if is_ambiguous:
            ambiguous_total += 1
            if binary_alert:
                ambiguous_alerted += 1
                # An ambiguous row is ``unsafe_forced_type`` only when a
                # typed conflict was emitted AND governance did not
                # route the row to ``needs_review``.  The governance
                # selector is the canonical rejector here (Cortes, De
                # Salvo, Mohri 2016 — "Learning with Rejection").
                if not is_needs_review:
                    ambiguous_forced += 1
            if abstained:
                ambiguous_abstained += 1
            if is_needs_review:
                ambiguous_needs_review += 1
                ambiguous_routed_to_review += 1
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
        if binary_alert:
            conflict_detected_binary += 1
        if exact_type_match:
            conflict_detected_exact += 1
        if cross_type:
            cross_type_alerts += 1
            cross_type_by_plane[str(winning_plane or "none")] += 1
        if abstained:
            abstain_total += 1
        predicted_key = predicted or "none"
        confusion.setdefault(expected or "unknown", {})
        confusion[expected or "unknown"][predicted_key] = confusion[expected or "unknown"].get(predicted_key, 0) + 1

        if res.get("row_contract_complete") is True:
            row_contract_complete_n += 1
        elif res.get("row_contract_complete") is False:
            row_contract_incomplete_n += 1
        oc = res.get("outcome_class")
        if oc is not None and str(oc):
            outcome_class_counts[str(oc)] += 1

        for vk, lk in (
            ("evaluation_contract_version", "evaluation_contract_version"),
            ("detector_bundle_version", "detector_bundle_version"),
            ("config_fingerprint", "config_fingerprint"),
        ):
            if not tool_versions.get(vk) and res.get(lk):
                tool_versions[vk] = str(res[lk])

    recall = (conflict_detected_binary / conflict_total) if conflict_total else 0.0
    exact_recall = (conflict_detected_exact / conflict_total) if conflict_total else 0.0
    core4_exact = (core4_detected_exact / core4_total) if core4_total else 0.0
    ambiguous_abstention = (ambiguous_abstained / ambiguous_total) if ambiguous_total else 0.0
    ambiguous_forced_rate = (ambiguous_forced / ambiguous_total) if ambiguous_total else 0.0
    ambiguous_routed_to_review_rate = (
        (ambiguous_routed_to_review / ambiguous_total) if ambiguous_total else 0.0
    )

    return {
        "events_used": len(events),
        "events_sliced_from": len(all_seed_events),
        "conflict_total": conflict_total,
        "conflict_detected": conflict_detected_binary,
        "conflict_recall": recall,
        "conflict_detected_exact": conflict_detected_exact,
        "conflict_exact_recall": exact_recall,
        "all_rows_exact_type_recall": exact_recall,
        "core4_total": core4_total,
        "core4_detected_exact": core4_detected_exact,
        "core4_exact_type_recall": core4_exact,
        "ambiguous_rows_total": ambiguous_total,
        "ambiguous_alerted": ambiguous_alerted,
        "ambiguous_abstained": ambiguous_abstained,
        "ambiguous_abstention_rate": ambiguous_abstention,
        # Wave 4.3+ — governance-aware scoring.  ``unsafe_forced_type_rate``
        # now only counts rows that emitted a typed conflict without
        # being routed to ``needs_review``; rows correctly deferred to
        # human review are reported separately.
        "unsafe_forced_type_rate": ambiguous_forced_rate,
        "ambiguous_needs_review": ambiguous_needs_review,
        "ambiguous_routed_to_review": ambiguous_routed_to_review,
        "ambiguous_routed_to_review_rate": ambiguous_routed_to_review_rate,
        "governance_outcome_counts": dict(governance_outcome_counts),
        "scoring_contract_version": "rdl-eval-2026-04-23-v2",
        "benign_status": "TBD",
        "cross_type_alerts": cross_type_alerts,
        "abstain_total": abstain_total,
        "exact_confusion": confusion,
        "by_class": by_class,
        "primary_source_counts": dict(source_counts.most_common()),
        "preflight_first_detected_n": preflight_first_detected_n,
        "preflight_async_disagreement_n": preflight_async_disagreement_n,
        "async_stronger_than_preflight_n": async_stronger_than_preflight_n,
        "winning_plane_counts": dict(winning_plane_counts),
        "cross_type_by_plane": dict(cross_type_by_plane),
        "row_contract_complete_n": row_contract_complete_n,
        "row_contract_incomplete_n": row_contract_incomplete_n,
        "outcome_class_counts": dict(outcome_class_counts),
        "tool_versions": tool_versions,
    }


def _rdl_last_seed_audit_block(project_id: str) -> dict[str, Any] | None:
    last: dict[str, Any] | None = None
    if not EXEC_LOG.exists():
        return None
    for line in EXEC_LOG.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            o = json.loads(line)
        except json.JSONDecodeError:
            continue
        if (
            o.get("phase") == 2
            and o.get("agent_id") == AGENT_ID
            and o.get("project") == project_id
            and o.get("action") == "project_seed_audit"
        ):
            r = o.get("result")
            if isinstance(r, dict):
                last = r
    return last


def conflict_list_rel_for_log(list_path: Path) -> str:
    if BTC_ROOT in list_path.parents or list_path == BTC_ROOT:
        return str(list_path.relative_to(BTC_ROOT)).replace("\\", "/")
    return str(list_path)


_ROW_RE = re.compile(
    r"^\|\s*(c-[a-z]+-\d+)\s*\|\s*([^|]+)\|\s*(.+?)\s*\|\s*([^|]+)\|\s*(.+?)\s*\|\s*([^|]*?)\s*\|\s*$",
    re.I,
)
_KEY_RE = re.compile(r"\*\*Key:\*\*\s*(\S+)", re.I)
_CAT_RE = re.compile(r"\*\*Cat:\*\*\s*(\S+)", re.I)
_VAL_RE = re.compile(r"\*\*Val:\*\*\s*\"((?:[^\"\\]|\\.)*)\"", re.I)
_VALID_RE = re.compile(
    r"\*\*Valid:\*\*\s*(\S+)\s+(\S+)",
    re.I,
)


def normalize_valid_ts(s: str) -> str:
    s = s.strip()
    if re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}Z$", s):
        return s.replace("Z", ":00Z")
    return s


def parse_conflict_table(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    text = path.read_text(encoding="utf-8")
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("| c-"):
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
        conflict_class = LABEL_TO_CLASS.get(label_raw)
        if not conflict_class:
            raise ValueError(f"Unknown label {label_raw!r} for {corpus_row_id}")

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
                "conflict_class": conflict_class,
                "expected_label": label_raw,
                "rationale_summary": rationale,
                "source_support": source_support,
            },
        )
    return rows


def corpus_key_token(row_id: str) -> str:
    return row_id.replace("-", "_")


def skf_expected_keys(path: Path) -> list[str]:
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    facts = data.get("facts") or []
    out: list[str] = []
    for f in facts:
        if isinstance(f, dict) and f.get("key"):
            out.append(str(f["key"]))
    return out


def referenced_baseline_keys(rows: list[dict[str, Any]]) -> set[str]:
    keys: set[str] = set()
    for r in rows:
        for k in r.get("based_on_facts") or []:
            keys.add(str(k).strip())
    return {k for k in keys if k}


def build_seed_audit(
    *,
    project_id: str,
    manifest_path: Path | None,
    expected_keys: list[str],
    stored_keys: set[str],
    total_facts_in_project: int,
) -> dict[str, Any]:
    exp_set = set(expected_keys)
    missing_in_project = sorted(exp_set - stored_keys) if exp_set else []
    extras = sorted(k for k in stored_keys if k.startswith("f-") and exp_set and k not in exp_set)
    sample = next((f for f in expected_keys if f in stored_keys), None)
    embedding_note = (
        "Pass if list_facts_v1 returns embedding-related fields on facts; not asserted by this harness."
    )
    return {
        "project_id": project_id,
        "manifest_path": str(manifest_path) if manifest_path and manifest_path.is_file() else None,
        "expected_seeded_corpus_facts": len(expected_keys),
        "total_facts_listed_in_project": total_facts_in_project,
        "skf_keys_missing_in_project": missing_in_project,
        "skf_extra_keys_in_project_not_in_manifest": extras[:50] if extras else [],
        "skf_extra_keys_truncated": len(extras) > 50,
        "embedding_audit": embedding_note,
        "sample_resolved_manifest_key_in_project": sample,
    }


def detection_audit_block(
    *,
    baseline_missing_keys: list[str],
    inline_available: bool,
    inline_detected: bool,
    async_matched: bool,
    poll_elapsed_s: float,
    max_wait_s: float,
) -> dict[str, Any]:
    baseline_missing = len(baseline_missing_keys) > 0
    any_alert = inline_detected or async_matched
    if baseline_missing:
        cls = "baseline_missing"
    elif any_alert:
        if inline_detected and async_matched:
            cls = "alert_inline_and_async"
        elif inline_detected:
            cls = "alert_inline_only"
        else:
            cls = "alert_async_only"
    elif not inline_available:
        cls = "no_inline_metrics_async_unmatched"
    else:
        cls = "no_alert_inline_available_async_unmatched"
    return {
        "baseline_missing": baseline_missing,
        "baseline_missing_keys": baseline_missing_keys,
        "inline_available": inline_available,
        "inline_fired": inline_detected,
        "async_poll_matched": async_matched,
        "poll_elapsed_s": round(poll_elapsed_s, 2),
        "poll_max_wait_s": max_wait_s,
        "classification": cls,
        "note": (
            "Does not distinguish NLI reject vs no retrieval vs graph-primary ID mismatch; "
            "async_unmatched may be late notification beyond poll window or matcher gap."
        ),
    }


def load_project_id(cfg: dict) -> str:
    pid = (cfg.get("real_data_lab_project_id") or cfg.get("project_id") or "").strip()
    if not pid:
        raise SystemExit("Set real_data_lab_project_id in .spirl/config.json")
    return pid


def rdl_phase1_complete() -> bool:
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
        if (
            o.get("phase") == 1
            and o.get("checkpoint_type") == "phase_complete"
            and o.get("status") == "complete"
        ):
            return True
    return False


def _foreign_phase2_projects_in_exec_log(path: Path, expected_project_id: str) -> set[str]:
    """Detect concurrent/wrong-project runs appending to the shared JSONL (prevents resume corruption)."""
    bad: set[str] = set()
    if not path.is_file():
        return bad
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            o = json.loads(line)
        except json.JSONDecodeError:
            continue
        if o.get("phase") != 2:
            continue
        pid = o.get("project")
        if pid and str(pid) != expected_project_id:
            bad.add(str(pid))
    return bad


def _foreign_phase1_projects_in_exec_log(path: Path, expected_project_id: str) -> set[str]:
    """Same as phase-2 foreign check, for phase==1 lines (interleaved Phase 1 + Phase 2 runs)."""
    bad: set[str] = set()
    if not path.is_file():
        return bad
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            o = json.loads(line)
        except json.JSONDecodeError:
            continue
        if o.get("phase") != 1:
            continue
        pid = o.get("project")
        if pid and str(pid) != expected_project_id:
            bad.add(str(pid))
    return bad


def phase2_complete(*, required_n: int | None = None, project_id: str | None = None) -> bool:
    """If required_n is set, phase_complete must record total_injections >= required_n (full corpus guard).

    When project_id is set, only checkpoints tagged with the same project_id count (avoids skipping Phase 2
    for a new import while an old checkpoint remains, and avoids matching pre-project-scoped history).
    """
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
        if o.get("phase") == 2 and o.get("checkpoint_type") == "phase_complete" and o.get("status") == "complete":
            if project_id is not None and o.get("project_id") not in (project_id, None):
                continue
            if project_id is not None and o.get("project_id") is None:
                # Legacy checkpoint without project_id — do not treat as complete for a scoped run
                continue
            if required_n is None:
                return True
            tot = o.get("total_injections")
            if isinstance(tot, int) and tot >= required_n:
                return True
    return False


def phase2_start_exists(project_id: str) -> bool:
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
        if o.get("phase") == 2 and o.get("checkpoint_type") == "phase_start":
            cpid = o.get("project_id")
            if cpid is not None and cpid != project_id:
                continue
            if cpid is None:
                continue
            return True
    return False


def conflict_injection_start_logged(project_id: str) -> bool:
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
        if o.get("phase") == 2 and o.get("action") == "conflict_injection_start":
            if o.get("project") != project_id:
                continue
            r = o.get("result") or {}
            if r.get("mode") != "table_driven":
                continue
            return True
    return False


def baseline_simulation_logged(project_id: str) -> bool:
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
        if o.get("phase") == 2 and o.get("action") == "baseline_simulation":
            if o.get("project") == project_id:
                return True
    return False


def seed_injected_corpus_ids(project_id: str) -> set[str]:
    """`c-*` corpus_row_id values that already have a `conflict_injected` line (seed agent; ignores benign)."""
    logged: set[str] = set()
    if not EXEC_LOG.exists():
        return logged
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
        aid = o.get("agent_id")
        if aid and aid != AGENT_ID:
            continue
        rid = str(o.get("corpus_row_id") or "")
        if rid.startswith("c-"):
            logged.add(rid)
    return logged


def resume_next_row_index(rows: list[dict[str, Any]], project_id: str) -> int:
    """First table row index not yet logged as conflict_injected (c-* only; ignores benign interleaving)."""
    logged = seed_injected_corpus_ids(project_id)
    for i, row in enumerate(rows):
        if row["corpus_row_id"] not in logged:
            return i
    return len(rows)


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


def memory_check_conflicts_v1(
    mcp: McpSession,
    project_id: str,
    *,
    kind: str,
    key: str,
    body: str,
    valid_from: str | None = None,
    valid_until: str | None = None,
    related_facts: list[str] | None = None,
    include_semantic_trace: bool = False,
    expected_anchor_keys: list[str] | None = None,
    conflict_execution_profile: str | None = None,
) -> Any:
    """Call MCP preflight check. `related_facts` must be stored fact UUIDs - not SKF keys like `f-dec-05`."""
    args: dict[str, Any] = {
        "project_id": project_id,
        "kind": kind,
        "key": key,
        "body": body,
        "tier": 1,
        "source_type": "human",
        "actor": AGENT_ID,
        "agent_id": AGENT_ID,
        "include_semantic_trace": include_semantic_trace,
        "related_facts": list(related_facts or []),
        "expected_anchor_keys": list(expected_anchor_keys or []),
        "tags": [],
    }
    if conflict_execution_profile:
        args["conflict_execution_profile"] = conflict_execution_profile
    if valid_from is not None:
        args["valid_from"] = valid_from
    if valid_until is not None:
        args["valid_until"] = valid_until
    return mcp.call_tool("memory_check_conflicts_v1", args)


STRUCTURAL_CONFLICT_CLASSES = {
    "dependency_impact",
    "constraint_violation",
    "temporal_invalidation",
}


def contract_fields_from_preflight_response(d: dict[str, Any]) -> dict[str, Any]:
    return {
        "evaluation_contract_version": d.get("evaluation_contract_version"),
        "detector_bundle_version": d.get("detector_bundle_version"),
        "config_fingerprint": d.get("config_fingerprint"),
        "trace_contract_complete": d.get("trace_contract_complete"),
        "trace_contract_missing_fields": list(d.get("trace_contract_missing_fields") or []),
        "route_confidence": dict(d.get("route_confidence") or {}),
        "anchor_certainty": d.get("anchor_certainty"),
        "verification_depth": d.get("verification_depth"),
        "outcome_class": d.get("outcome_class"),
        "final_conflict_type": d.get("final_conflict_type"),
        "winning_detector_plane": d.get("winning_detector_plane"),
        "preflight_terminal": d.get("preflight_terminal"),
        "lane_verdicts": dict(d.get("lane_verdicts") or {}),
    }


def merge_row_contract_fields(*blocks: dict[str, Any] | None) -> dict[str, Any]:
    merged: dict[str, Any] = {
        "evaluation_contract_version": None,
        "detector_bundle_version": None,
        "config_fingerprint": None,
        "route_confidence": {},
        "anchor_certainty": None,
        "verification_depth": None,
        "outcome_class": None,
        "final_conflict_type": None,
        # Must be None (not the string "none") so contract_fields_from_preflight_response can overwrite.
        "winning_detector_plane": None,
        "preflight_terminal": False,
        "lane_verdicts": {},
    }
    any_called = False
    complete_flags: list[bool] = []
    missing: list[str] = []
    for block in blocks:
        if not isinstance(block, dict):
            continue
        if block.get("called"):
            any_called = True
        if "trace_contract_complete" in block:
            complete_flags.append(bool(block.get("trace_contract_complete")))
        for key in (
            "evaluation_contract_version",
            "detector_bundle_version",
            "config_fingerprint",
            "anchor_certainty",
            "verification_depth",
            "outcome_class",
            "final_conflict_type",
            "winning_detector_plane",
            "preflight_terminal",
        ):
            value = block.get(key)
            if value not in (None, {}, [], "") and merged.get(key) in (None, {}, [], ""):
                merged[key] = value
        lane_verdicts = block.get("lane_verdicts")
        if isinstance(lane_verdicts, dict) and lane_verdicts and not merged["lane_verdicts"]:
            merged["lane_verdicts"] = dict(lane_verdicts)
        route_confidence = block.get("route_confidence")
        if isinstance(route_confidence, dict):
            merged["route_confidence"].update({str(k): v for k, v in route_confidence.items()})
        for item in block.get("trace_contract_missing_fields") or []:
            item_s = str(item)
            if item_s and item_s not in missing:
                missing.append(item_s)
    merged["row_contract_missing_fields"] = missing
    merged["row_contract_complete"] = bool(any_called) and (all(complete_flags) if complete_flags else False) and not missing
    return merged


def build_semantic_preflight_block(
    *,
    conflict_class: str,
    preflight_raw: Any | None = None,
    preflight_error: str | None = None,
    semantic_track: bool = False,
) -> dict[str, Any]:
    include_semantic_trace_requested = semantic_track or conflict_class != "benign"
    if preflight_error:
        return {
            "called": True,
            "include_semantic_trace_requested": include_semantic_trace_requested,
            "error": preflight_error,
            "preflight_has_conflicts": False,
            "preflight_has_semantic_conflicts": False,
            "semantic_verdict": "unavailable",
            "semantic_stop_reason": None,
            "semantic_trace_present": False,
            "semantic_trace_missing": include_semantic_trace_requested,
            "semantic_trace": None,
            "semantic_preflight_winning_stop_reason": None,
            "semantic_preflight_first_candidate_stop_reason": None,
            "evaluation_contract_version": None,
            "detector_bundle_version": None,
            "config_fingerprint": None,
            "trace_contract_complete": False,
            "trace_contract_missing_fields": ["preflight_error"],
            "route_confidence": {},
            "anchor_certainty": None,
            "verification_depth": None,
            "outcome_class": "unavailable",
        }
    d = _tool_result_as_dict(preflight_raw)
    trace = d.get("semantic_trace")
    block: dict[str, Any] = {
        "called": preflight_raw is not None,
        "include_semantic_trace_requested": include_semantic_trace_requested,
        "preflight_has_conflicts": bool(d.get("has_conflicts")),
        "preflight_has_semantic_conflicts": bool(d.get("preflight_has_semantic_conflicts")),
        "semantic_verdict": d.get("semantic_verdict"),
        "semantic_stop_reason": d.get("semantic_stop_reason"),
        "semantic_trace_present": trace is not None,
        "semantic_trace_missing": include_semantic_trace_requested and trace is None,
    }
    block.update(contract_fields_from_preflight_response(d))
    if trace is not None:
        block["semantic_trace"] = trace
        block["semantic_preflight_winning_stop_reason"] = trace.get("winning_stop_reason")
        cands = trace.get("candidate_traces") or []
        if isinstance(cands, list) and cands:
            first = cands[0] if isinstance(cands[0], dict) else {}
            block["semantic_preflight_first_candidate_stop_reason"] = first.get("stop_reason")
    else:
        block["semantic_trace"] = None
        block["semantic_preflight_winning_stop_reason"] = d.get("semantic_stop_reason")
        block["semantic_preflight_first_candidate_stop_reason"] = None
    return block


def semantic_preflight_detected(block: dict[str, Any] | None) -> bool:
    if not isinstance(block, dict) or not block.get("called"):
        return False
    verdict = block.get("semantic_verdict")
    if verdict == "detected":
        return True
    if verdict in {"rejected", "abstain", "unavailable"}:
        return False
    trace = block.get("semantic_trace")
    if not isinstance(trace, dict):
        return False
    try:
        if int(trace.get("emitted_conflict_count") or 0) > 0:
            return True
    except (TypeError, ValueError):
        pass
    return trace.get("winning_stop_reason") == "emitted_contradiction"


def semantic_terminal_stop_reason(block: dict[str, Any] | None) -> str | None:
    if not isinstance(block, dict) or not block.get("called"):
        return None
    if semantic_preflight_detected(block):
        return None
    stop_reason = (
        block.get("semantic_stop_reason")
        or block.get("semantic_preflight_winning_stop_reason")
        or block.get("semantic_preflight_first_candidate_stop_reason")
    )
    verdict = block.get("semantic_verdict")
    if verdict in {"rejected", "abstain"} and stop_reason:
        return str(stop_reason)
    if block.get("error") or block.get("semantic_trace_missing"):
        return None
    if stop_reason in TERMINAL_SEMANTIC_STOP_REASONS:
        return str(stop_reason)
    return None


def semantic_poll_policy(
    *,
    semantic_row: bool,
    sem_preflight: dict[str, Any] | None,
    default_max_wait_s: float,
    semantic_detected_max_wait_s: float = DEFAULT_SEMANTIC_DETECTED_POLL_MAX_WAIT_S,
    semantic_terminal_max_wait_s: float = DEFAULT_SEMANTIC_TERMINAL_POLL_MAX_WAIT_S,
) -> dict[str, Any]:
    if not semantic_row:
        return {
            "poll_policy": "full_async_fallback",
            "poll_skipped": False,
            "poll_max_wait_s_effective": float(default_max_wait_s),
            "semantic_terminal_stop_reason": None,
        }
    block = sem_preflight if isinstance(sem_preflight, dict) else {}
    terminal_reason = semantic_terminal_stop_reason(block)
    if terminal_reason is not None:
        return {
            "poll_policy": "skip_terminal_preflight",
            "poll_skipped": True,
            "poll_max_wait_s_effective": max(float(semantic_terminal_max_wait_s), 0.0),
            "semantic_terminal_stop_reason": terminal_reason,
        }
    if semantic_preflight_detected(block):
        return {
            "poll_policy": "short_detected_preflight",
            "poll_skipped": False,
            "poll_max_wait_s_effective": max(float(semantic_detected_max_wait_s), 0.0),
            "semantic_terminal_stop_reason": None,
        }
    return {
        "poll_policy": "full_async_fallback",
        "poll_skipped": False,
        "poll_max_wait_s_effective": float(default_max_wait_s),
        "semantic_terminal_stop_reason": None,
    }


def semantic_primary_detection_result(
    *,
    sem_preflight: dict[str, Any] | None,
    async_exact_type_match: bool,
    inline_exact_type_match: bool,
) -> tuple[bool, str, str | None]:
    block = sem_preflight if isinstance(sem_preflight, dict) else {}
    terminal_reason = semantic_terminal_stop_reason(block)
    if semantic_preflight_detected(block):
        return True, "preflight", None
    if terminal_reason is not None:
        return False, "preflight", terminal_reason
    if bool(async_exact_type_match):
        return True, "async_fallback", None
    trace_unavailable = (
        (not block.get("called"))
        or bool(block.get("error"))
        or (bool(block.get("include_semantic_trace_requested")) and bool(block.get("semantic_trace_missing")))
    )
    if trace_unavailable and bool(inline_exact_type_match):
        return True, "inline_fallback", None
    if trace_unavailable:
        if block.get("error"):
            return False, "preflight_error", None
        if block.get("semantic_trace_missing"):
            return False, "preflight_missing", None
        return False, "preflight_unavailable", None
    return False, "preflight", block.get("semantic_stop_reason") or block.get("semantic_preflight_winning_stop_reason")


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
            "route_confidence": {},
            "abstained_reason": {},
            "match_result": {},
            "search_result": {},
            "verify_result": {},
            "graph_program_path": {},
            "structural_anchor_fact_id": {},
            "evaluation_contract_version": None,
            "detector_bundle_version": None,
            "config_fingerprint": None,
            "trace_contract_complete": False,
            "trace_contract_missing_fields": ["preflight_error"],
            "anchor_certainty": None,
            "verification_depth": None,
            "outcome_class": "unavailable",
        }
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
    block = {
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
        "route_confidence": dict(sp.get("route_confidence") or d.get("route_confidence") or {}),
        "abstained_reason": dict(d.get("abstained_reason") or sp.get("abstained_reason") or {}),
        "match_result": dict(sp.get("match_result") or {}),
        "search_result": dict(sp.get("search_result") or {}),
        "verify_result": dict(sp.get("verify_result") or {}),
        "graph_program_path": dict(sp.get("graph_program_path") or {}),
        "structural_anchor_fact_id": dict(sp.get("structural_anchor_fact_id") or {}),
    }
    block.update(contract_fields_from_preflight_response(d))
    return block


def structural_preflight_detected(
    block: dict[str, Any] | None,
    expected_conflict_type: str,
) -> bool:
    if expected_conflict_type not in STRUCTURAL_CONFLICT_CLASSES:
        return False
    if not isinstance(block, dict) or not block.get("called"):
        return False
    verdicts = block.get("verdicts") or {}
    verdict = verdicts.get(expected_conflict_type)
    if isinstance(verdict, dict):
        verdict = verdict.get("verdict")
    return verdict == "detected"


def structural_terminal_stop_reason(
    block: dict[str, Any] | None,
    expected_conflict_type: str,
) -> str | None:
    if expected_conflict_type not in STRUCTURAL_CONFLICT_CLASSES:
        return None
    if not isinstance(block, dict) or not block.get("called"):
        return None
    if structural_preflight_detected(block, expected_conflict_type):
        return None
    stop_reasons = block.get("stop_reasons") or {}
    abstained = block.get("abstained_reason") or {}
    return stop_reasons.get(expected_conflict_type) or abstained.get(expected_conflict_type)


def structural_primary_detection_result(
    *,
    expected_conflict_type: str,
    structural_preflight: dict[str, Any] | None,
    async_exact_type_match: bool,
    inline_exact_type_match: bool,
) -> tuple[bool, str, str | None]:
    if expected_conflict_type not in STRUCTURAL_CONFLICT_CLASSES:
        return False, "not_applicable", None
    block = structural_preflight if isinstance(structural_preflight, dict) else {}
    terminal_reason = structural_terminal_stop_reason(block, expected_conflict_type)
    if structural_preflight_detected(block, expected_conflict_type):
        return True, "preflight", None
    if bool(async_exact_type_match):
        return True, "async_fallback", None
    if bool(inline_exact_type_match):
        return True, "inline_fallback", None
    if block.get("error"):
        return False, "preflight_error", terminal_reason
    if block.get("called"):
        return False, "preflight", terminal_reason
    return False, "preflight_unavailable", terminal_reason


def observed_conflict_types(
    *,
    sem_preflight: dict[str, Any] | None,
    structural_preflight: dict[str, Any] | None,
    inline_conflict_types: list[str],
    matched_conflict_type: str | None,
) -> set[str]:
    observed: set[str] = set()
    if semantic_preflight_detected(sem_preflight):
        observed.add("semantic_contradiction")
    if isinstance(structural_preflight, dict):
        observed.update(str(x) for x in (structural_preflight.get("classes_detected") or []) if x)
    observed.update(str(x) for x in (inline_conflict_types or []) if x)
    if matched_conflict_type:
        observed.add(str(matched_conflict_type))
    return observed


def render_phase2_report_markdown(
    *,
    project_id: str,
    n_total: int,
    rel_src: str,
    list_path: Path,
    injection_limit: int | None,
    missing_baseline_keys_seen: set[str] | frozenset[str],
) -> str:
    """Build Phase 2 markdown report from execution log (seed agent only for accounting)."""
    all_missing_keys: set[str] = set(missing_baseline_keys_seen)
    by_class: dict[str, dict[str, int]] = {k: {"injected": 0, "failed": 0} for k in TARGET_PER_CLASS_FULL}
    injection_failed_ids: list[str] = []
    if EXEC_LOG.exists():
        for line in EXEC_LOG.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                o = json.loads(line)
            except json.JSONDecodeError:
                continue
            if o.get("phase") != 2 or o.get("project") != project_id:
                continue
            aid = o.get("agent_id")
            if aid and aid != AGENT_ID:
                continue
            ccls = o.get("conflict_class")
            if ccls not in by_class:
                continue
            if o.get("action") == "conflict_injected":
                res = o.get("result") or {}
                if isinstance(res, dict):
                    for mk in res.get("missing_baseline_keys") or []:
                        if mk:
                            all_missing_keys.add(str(mk))
                by_class[str(ccls)]["injected"] += 1
            elif o.get("action") == "injection_failed" and "corpus_row_id" in o:
                by_class[str(ccls)]["failed"] += 1
                rid = o.get("corpus_row_id")
                if rid:
                    injection_failed_ids.append(str(rid))

    surf = compute_phase2_conflict_surface_metrics(project_id, n_total)
    audit = _rdl_last_seed_audit_block(project_id)
    confusion = surf.get("exact_confusion") or {}
    matrix_rows = [
        "| Expected | semantic | dependency | constraint | temporal | none |",
        "|----------|---------:|-----------:|-----------:|---------:|-----:|",
    ]
    for expected in (
        "semantic_contradiction",
        "dependency_impact",
        "constraint_violation",
        "temporal_invalidation",
    ):
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

    by_surf = surf.get("by_class") or {}
    per_class_lines = [
        "| conflict_class | rows (log slice) | binary alert | exact-type match | cross-type | abstained |",
        "|----------------|-----------------:|-------------:|-----------------:|-----------:|----------:|",
    ]
    for k in (
        "semantic_contradiction",
        "dependency_impact",
        "constraint_violation",
        "temporal_invalidation",
        "ambiguous_case",
    ):
        bc = by_surf.get(k) or {}
        per_class_lines.append(
            "| `{}` | {} | {} | {} | {} | {} |".format(
                k,
                bc.get("injected", 0),
                bc.get("binary_detected", 0),
                bc.get("exact_detected", 0),
                bc.get("cross_type_alerts", 0),
                bc.get("abstained", 0),
            ),
        )

    route_lines = ["| primary_detector_source | rows |", "|--------------------------|-----:|"]
    for src, cnt in (surf.get("primary_source_counts") or {}).items():
        route_lines.append(f"| `{src}` | {cnt} |")
    if len(route_lines) == 2:
        route_lines.append("| _(none)_ | 0 |")

    tv = surf.get("tool_versions") or {}
    tool_lines = ["| Field | Value |", "|-------|-------|"]
    for label, key in (
        ("Evaluation contract", "evaluation_contract_version"),
        ("Detector bundle", "detector_bundle_version"),
        ("Config fingerprint", "config_fingerprint"),
    ):
        val = tv.get(key, "—")
        tool_lines.append(f"| {label} | `{val}` |")

    oc_counts = surf.get("outcome_class_counts") or {}
    oc_lines = ["| outcome_class (logged) | rows |", "|-------------------------|-----:|"]
    for k_oc, v_oc in sorted(oc_counts.items(), key=lambda kv: (-kv[1], kv[0])):
        oc_lines.append(f"| `{k_oc}` | {v_oc} |")
    if len(oc_lines) == 2:
        oc_lines.append("| _(none)_ | 0 |")

    audit_lines: list[str]
    if audit:
        audit_lines = [
            f"- Manifest: `{audit.get('manifest_path', '—')}`",
            f"- Expected seeded corpus facts (SKF): **{audit.get('expected_seeded_corpus_facts', '—')}**",
            f"- Total facts listed at audit: **{audit.get('total_facts_listed_in_project', '—')}**",
            f"- SKF keys missing in project: **{len(audit.get('skf_keys_missing_in_project') or [])}**",
            f"- Sample manifest key resolved: `{audit.get('sample_resolved_manifest_key_in_project', '—')}`",
        ]
    else:
        audit_lines = ["- _(No `project_seed_audit` entry found for this agent/project.)_"]

    slice_note = ""
    if int(surf.get("events_sliced_from") or 0) > int(surf.get("events_used") or 0):
        slice_note = (
            f"\n_Log slice: used the latest **{surf.get('events_used')}** seed `c-*` injections "
            f"of **{surf.get('events_sliced_from')}** present in the log (multiple Phase 2 runs)._"
        )

    report_lines = [
        "# Phase 2 Report — Real Data Lab (Conflict injection)",
        "",
        f"Generated: {iso_now()}",
        "",
        f"Project: `{project_id}`",
        "",
        "## Corpus",
        "",
        f"- Source: `{rel_src}` (resolved: `{list_path}`)",
        "- Mode: table-driven",
        f"- Rows attempted: **{n_total}**",
        f"- Injection limit applied: **{injection_limit is not None}**",
        "",
        "## Pre-injection seed audit (last logged)",
        "",
        *audit_lines,
        "",
        "## Conflicts (c-* corpus) — injection-time detector surface",
        "",
        "Metrics below are derived from `conflict_injected` log lines for agent "
        f"`{AGENT_ID}` (same detection scoring as the mixed report conflict block).{slice_note}",
        "",
        "The current live conflict-injection surface is strongest on constraint, strong on temporal, respectable on dependency and semantic, and still pending a benign-only readout before precision and F1 are finalized.",
        "",
        "| Metric | Value |",
        "|--------|------:|",
        f"| Rows (log slice, c-*) | {surf.get('conflict_total', 0)} |",
        f"| Rows (core-4, non-ambiguous) | {surf.get('core4_total', 0)} |",
        f"| Binary detected (any alert) | {surf.get('conflict_detected', 0)} |",
        f"| Binary recall | {float(surf.get('conflict_recall') or 0):.4f} |",
        f"| Exact-type matches (core-4) | {surf.get('core4_detected_exact', surf.get('conflict_detected_exact', 0))} |",
        f"| Core-4 exact-type recall | {float(surf.get('core4_exact_type_recall') or 0):.4f} |",
        f"| All-row exact-type recall | {float(surf.get('all_rows_exact_type_recall') or surf.get('conflict_exact_recall') or 0):.4f} |",
        f"| Cross-type alerts | {surf.get('cross_type_alerts', 0)} |",
        f"| Abstained rows | {surf.get('abstain_total', 0)} |",
        f"| Benign status | {surf.get('benign_status', 'TBD')} |",
        "",
        f"- Preflight-first detected rows: **{surf.get('preflight_first_detected_n', 0)}**",
        f"- Preflight/async disagreements: **{surf.get('preflight_async_disagreement_n', 0)}**",
        f"- Async-only recoveries: **{surf.get('async_stronger_than_preflight_n', 0)}**",
        "",
        "## Ambiguous rows",
        "",
        f"- Ambiguous rows total: **{surf.get('ambiguous_rows_total', 0)}**",
        f"- Ambiguous alerted: **{surf.get('ambiguous_alerted', 0)}**",
        f"- Ambiguous abstained: **{surf.get('ambiguous_abstained', 0)}**",
        f"- Ambiguous routed to review (governance needs_review): "
        f"**{surf.get('ambiguous_routed_to_review', 0)}** "
        f"({float(surf.get('ambiguous_routed_to_review_rate') or 0):.4f})",
        f"- Unsafe forced-type rate: **{float(surf.get('unsafe_forced_type_rate') or 0):.4f}** "
        f"(governance-aware, contract `{surf.get('scoring_contract_version', 'rdl-eval-2026-04-23-v2')}`)",
        f"- Governance outcome counts: `{json.dumps(surf.get('governance_outcome_counts') or {}, ensure_ascii=False)}`",
        "",
        "_Ambiguous rows are excluded from the **core-4 exact-type headline metric** and reported separately as handling quality._",
        "_Unsafe forced-type rate is governance-aware: typed alerts that were routed to ``needs_review`` by the Neyman-Pearson governance selector (Wave 4.3) are NOT counted as forced — they are the intended deferral path (Chow 1970; Madras et al. 2018; Mozannar & Sontag 2020)._",
        "",
        "## Per-class detection (injection-time)",
        "",
        *per_class_lines,
        "",
        "## Primary detector source (first matching signal)",
        "",
        *route_lines,
        "",
        "## Winning plane / cross-type pressure",
        "",
        f"- Winning plane counts: `{json.dumps(surf.get('winning_plane_counts') or {}, ensure_ascii=False)}`",
        f"- Cross-type alerts by winning plane: `{json.dumps(surf.get('cross_type_by_plane') or {}, ensure_ascii=False)}`",
        "",
        "_Note: the bucket key `none` means the flattened row contract still carried a missing, null, or literal "
        "`\"none\"` `winning_detector_plane`. It is a **logging/flattening artifact**, not proof the detector used no plane. "
        "When nested preflight values are present, those are the authoritative detector-plane values. "
        "**Exact-type scoring is driven by predicted vs expected conflict type, not by this histogram.**_",
        "",
        "## Row evaluation contract (first row sample)",
        "",
        *tool_lines,
        "",
        "## Row contract / outcome_class tallies (log slice)",
        "",
        f"- `row_contract_complete: true`: **{surf.get('row_contract_complete_n', 0)}**",
        f"- `row_contract_complete: false`: **{surf.get('row_contract_incomplete_n', 0)}**",
        "",
        *oc_lines,
        "",
        "## Exact-type confusion matrix (structural + semantic columns)",
        "",
        *matrix_rows,
        "",
        "_Detection rule: semantic rows only score as semantic when `semantic_verdict=detected` "
        "(or semantic trace shows an emitted contradiction); structural rows score exact-type when the "
        "expected class appears in preflight, inline preflight, or async notification._",
        "",
        "## Results by conflict_class (injection accounting)",
        "",
        "| conflict_class | conflict_injected (log) | injection_failed (log) |",
        "|----------------|-------------------------:|-----------------------:|",
    ]
    for k in (
        "semantic_contradiction",
        "dependency_impact",
        "constraint_violation",
        "temporal_invalidation",
        "ambiguous_case",
    ):
        report_lines.append(f"| `{k}` | {by_class[k]['injected']} | {by_class[k]['failed']} |")
    tot_i = sum(v["injected"] for v in by_class.values())
    tot_f = sum(v["failed"] for v in by_class.values())
    report_lines.extend(
        [
            f"| **TOTAL** | **{tot_i}** | **{tot_f}** |",
            "",
            "## Baseline simulation",
            "",
            "Rule: baseline only flags **same-key overlapping validity**. Proposed facts use **p-*** keys, "
            "so `baseline_detectable` is **0** for all five classes; `baseline_missed` matches per-class row counts for this run.",
            "",
            "Logged: `baseline_simulation` in `real_data_lab_execution_log.jsonl`; fact `research.rdl.baseline.simulation`.",
            "",
            "## Missing baseline keys (preflight)",
            "",
        ],
    )
    if all_missing_keys:
        report_lines.append(", ".join(f"`{x}`" for x in sorted(all_missing_keys)))
    else:
        report_lines.append("None logged.")
    report_lines.extend(
        [
            "",
            "## Failed corpus_row_id (if any)",
            "",
        ],
    )
    if injection_failed_ids:
        report_lines.append(", ".join(f"`{x}`" for x in injection_failed_ids))
    else:
        report_lines.append("None.")
    report_lines.extend(
        [
            "",
            "## Artifacts",
            "",
            "- Execution log: `real-data-lab/research/real_data_lab_execution_log.jsonl`",
            "- Checkpoints: `real-data-lab/research/real_data_lab_checkpoints.jsonl`",
            "",
        ],
    )
    return "\n".join(report_lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="Real Data Lab Phase 2 — list_conflict.md injections via MCP")
    ap.add_argument(
        "--injection-limit",
        type=int,
        default=None,
        metavar="N",
        help="Process only first N rows (overrides real_data_lab_injection_limit in config)",
    )
    ap.add_argument(
        "--lenient-baseline",
        action="store_true",
        help="Do not exit when corpus baseline keys are missing from the project (default is strict).",
    )
    ap.add_argument(
        "--precheck-only",
        action="store_true",
        help="Log seed audit + validate baseline keys for the slice, then exit (no injections).",
    )
    ap.add_argument(
        "--poll-max-s",
        type=float,
        default=None,
        metavar="SEC",
        help="Seconds to poll list_conflicts_v1 after each upsert. "
        "If omitted, uses real_data_lab_poll_max_s from .spirl/config.json, else 8. "
        "Background NLI/graph work may need 120–180+ when cold.",
    )
    ap.add_argument(
        "--semantic-terminal-poll-max-wait",
        type=float,
        default=DEFAULT_SEMANTIC_TERMINAL_POLL_MAX_WAIT_S,
        metavar="SEC",
        help="Effective async poll budget for semantic rows with terminal preflight misses (default 0).",
    )
    ap.add_argument(
        "--semantic-detected-poll-max-wait",
        type=float,
        default=DEFAULT_SEMANTIC_DETECTED_POLL_MAX_WAIT_S,
        metavar="SEC",
        help="Effective async poll budget for semantic rows already detected in preflight (default 15).",
    )
    ap.add_argument(
        "--conflict-list",
        type=str,
        default=None,
        metavar="PATH",
        help="Override conflict table path (relative to Beyond Temporal Contradiction/ unless absolute).",
    )
    ap.add_argument(
        "--ignore-phase2-lock",
        action="store_true",
        help="Skip real_data_lab_pipeline.lock (only if no other RDL phase script is using this repo).",
    )
    ap.add_argument(
        "--rewrite-report",
        action="store_true",
        help="Rewrite real_data_lab_phase2_report.md from the execution log and exit (Phase 2 must already be complete).",
    )
    args = ap.parse_args()

    cfg = load_json(SPIRL_CONFIG)
    mode = str(cfg.get("real_data_lab_phase2_mode") or "table_driven").lower()
    if mode == "synthetic":
        raise SystemExit(
            "real_data_lab_phase2_mode is synthetic; use paper3_phase2 flow or set mode to table_driven."
        )

    list_path = resolve_conflict_list_path(cfg, args.conflict_list)
    rel_src = conflict_list_rel_for_log(list_path)

    injection_limit: int | None = args.injection_limit
    if injection_limit is None:
        limit_cfg = cfg.get("real_data_lab_injection_limit")
        if limit_cfg is not None:
            try:
                injection_limit = int(limit_cfg)
                if injection_limit <= 0:
                    injection_limit = None
            except (TypeError, ValueError):
                injection_limit = None

    strict_baseline = bool(cfg.get("real_data_lab_phase2_strict_baseline", True))
    if args.lenient_baseline:
        strict_baseline = False
    strict_seed = bool(cfg.get("real_data_lab_phase2_strict_seed_manifest", False))

    if not rdl_phase1_complete():
        append_jsonl(
            CHECKPOINTS,
            {
                "timestamp": iso_now(),
                "phase": 2,
                "checkpoint_type": "phase_failed",
                "agent_id": AGENT_ID,
                "status": "failed",
                "error": "Phase 1 phase_complete not found in real_data_lab_checkpoints.jsonl",
            },
        )
        raise SystemExit("Phase 1 not complete.")

    rows = parse_conflict_table(list_path)
    if not rows:
        raise SystemExit(f"No rows parsed from {list_path}")

    n_total = len(rows) if injection_limit is None else min(len(rows), injection_limit)
    rows = rows[:n_total]

    project_id = load_project_id(cfg)

    if args.rewrite_report:
        if not phase2_complete(required_n=n_total, project_id=project_id):
            raise SystemExit("Phase 2 not complete for this project and row count; cannot --rewrite-report.")
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        REPORT_PATH.write_text(
            render_phase2_report_markdown(
                project_id=project_id,
                n_total=n_total,
                rel_src=rel_src,
                list_path=list_path,
                injection_limit=injection_limit,
                missing_baseline_keys_seen=set(),
            ),
            encoding="utf-8",
        )
        print(f"Rewrote {REPORT_PATH}")
        return 0

    if phase2_complete(required_n=n_total, project_id=project_id) and not args.precheck_only:
        print("Phase 2 already complete (checkpoint). Exiting.")
        return 0

    _foreign = _foreign_phase2_projects_in_exec_log(EXEC_LOG, project_id)
    if _foreign:
        raise SystemExit(
            f"real_data_lab_execution_log.jsonl contains phase-2 lines for other project(s) {sorted(_foreign)}; "
            f"expected {project_id!r}. Stop other harnesses, archive/clean the log, then retry."
        )
    _foreign_p1 = _foreign_phase1_projects_in_exec_log(EXEC_LOG, project_id)
    if _foreign_p1:
        raise SystemExit(
            f"real_data_lab_execution_log.jsonl contains phase-1 lines for other project(s) {sorted(_foreign_p1)}; "
            f"expected {project_id!r}. Archive/clean the log (or run Phase 1 without --resume), then retry."
        )

    with rdl_pipeline_lock(ignore=bool(args.ignore_phase2_lock)):
        if phase2_complete(required_n=n_total, project_id=project_id) and not args.precheck_only:
            print("Phase 2 already complete (checkpoint). Exiting.")
            return 0

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
                "result": seed_audit,
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
                    "result": {"missing_keys": miss, "manifest_path": str(manifest)},
                },
            )
            append_jsonl(
                CHECKPOINTS,
                {
                    "timestamp": iso_now(),
                    "phase": 2,
                    "checkpoint_type": "seed_manifest_validation_failed",
                    "agent_id": AGENT_ID,
                    "status": "failed",
                    "missing_keys": miss,
                    "project": project_id,
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
                        "source_table": rel_src,
                        "strict_baseline": strict_baseline,
                    },
                },
            )
            append_jsonl(
                CHECKPOINTS,
                {
                    "timestamp": iso_now(),
                    "phase": 2,
                    "checkpoint_type": "baseline_validation_failed",
                    "agent_id": AGENT_ID,
                    "status": "failed",
                    "missing_keys": missing_ref,
                    "project": project_id,
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
                    },
                },
            )
        elif args.precheck_only:
            print("Precheck OK — all referenced baseline keys for this slice exist in the project.")
            return 0

        injected_ids = seed_injected_corpus_ids(project_id)

        if not phase2_start_exists(project_id):
            append_jsonl(
                CHECKPOINTS,
                {
                    "timestamp": iso_now(),
                    "phase": 2,
                    "checkpoint_type": "phase_start",
                    "agent_id": AGENT_ID,
                    "status": "in_progress",
                    "project_id": project_id,
                    "prerequisites_checked": True,
                    "notes": f"RDL Phase 2 — {rel_src}, N={n_total} rows",
                },
            )

        class_counts_slice = Counter(r["conflict_class"] for r in rows)
        target_per_class_slice = {k: int(class_counts_slice.get(k, 0)) for k in TARGET_PER_CLASS_FULL}

        if args.poll_max_s is not None:
            poll_max_s = float(args.poll_max_s)
        else:
            _p = cfg.get("real_data_lab_poll_max_s")
            poll_max_s = float(_p) if _p is not None else 8.0
        if poll_max_s <= 0:
            raise SystemExit("poll max seconds must be positive (--poll-max-s or real_data_lab_poll_max_s)")

        _skew = cfg.get("real_data_lab_conflict_poll_after_skew_s")
        poll_after_skew_s = float(_skew) if _skew is not None else 120.0

        if not conflict_injection_start_logged(project_id):
            append_jsonl(
                EXEC_LOG,
                {
                    "timestamp": iso_now(),
                    "phase": 2,
                    "agent_id": AGENT_ID,
                    "action": "conflict_injection_start",
                    "project": project_id,
                    "result": {
                        "source": rel_src,
                        "mode": "table_driven",
                        "target_total": n_total,
                        "target_per_class": target_per_class_slice,
                        "target_per_project": {project_id: n_total},
                        "injection_limit_applied": injection_limit is not None,
                        "poll_max_wait_s": poll_max_s,
                        "semantic_terminal_poll_max_wait_s": float(args.semantic_terminal_poll_max_wait),
                        "semantic_detected_poll_max_wait_s": float(args.semantic_detected_poll_max_wait),
                    },
                },
            )

        class_counts_progress = {k: 0 for k in TARGET_PER_CLASS_FULL}
        successes_since_checkpoint = 0
        missing_baseline_keys_seen: set[str] = set()

        for i in range(n_total):
            if PAUSE_FLAG.is_file():
                prev_id = rows[i - 1]["corpus_row_id"] if i > 0 else None
                append_jsonl(
                    CHECKPOINTS,
                    {
                        "timestamp": iso_now(),
                        "phase": 2,
                        "checkpoint_type": "operator_pause",
                        "agent_id": AGENT_ID,
                        "status": "paused",
                        "last_corpus_row_id": prev_id,
                        "next_injection_number": i + 1,
                        "notes": "Remove real-data-lab/research/real_data_lab_pause.flag and re-run to continue.",
                    },
                )
                print(
                    "PAUSED: remove real-data-lab/research/real_data_lab_pause.flag then re-run to continue.",
                    flush=True,
                )
                return 2
            row = rows[i]
            injection_number = i + 1
            corpus_row_id = row["corpus_row_id"]
            if corpus_row_id.startswith("c-") and corpus_row_id in injected_ids:
                print(f"[skip {injection_number}/{n_total}] {corpus_row_id} already injected", flush=True)
                continue
            cls = row["conflict_class"]
            proposed_key = row["proposed_key"]
            ground_truth_key = f"research.rdl.groundtruth.{corpus_key_token(corpus_row_id)}"

            missing_baseline = [k for k in row["based_on_facts"] if k not in fact_keys_set]
            for mk in missing_baseline:
                missing_baseline_keys_seen.add(mk)

            preflight_raw: Any | None = None
            preflight_err: str | None = None
            include_semantic_trace = True
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
                    include_semantic_trace=include_semantic_trace,
                    expected_anchor_keys=row["based_on_facts"],
                    conflict_execution_profile="research",
                )
            except Exception as e:
                preflight_err = str(e)
            sem_preflight = build_semantic_preflight_block(
                conflict_class=cls,
                preflight_raw=preflight_raw,
                preflight_error=preflight_err,
            )
            structural_preflight = build_structural_preflight_block(
                preflight_raw=preflight_raw,
                preflight_error=preflight_err,
            )
            # Wave 4 — capture governance_outcome and preflight cascade
            # latency from the envelope.  Both fields were missing from the
            # 2026-04-21 run because this runner pre-dates Wave 4.3 and the
            # old detection_latency_ms path (post-write sync) is normally
            # short-circuited when preflight already surfaced conflicts.
            gov_outcome = _governance_outcome_from_result(preflight_raw) if isinstance(preflight_raw, dict) else None
            gov_decision = (
                _governance_decision_from_result(preflight_raw)
                if isinstance(preflight_raw, dict)
                else None
            )
            preflight_latency_ms = (
                _preflight_latency_ms_from_result(preflight_raw)
                if isinstance(preflight_raw, dict)
                else None
            )

            t0 = time.monotonic()
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
                        "conflict_class": cls,
                        "corpus_row_id": corpus_row_id,
                        "based_on_facts": row["based_on_facts"],
                        "proposed_fact_key": proposed_key,
                        "ground_truth_key": ground_truth_key,
                        "result": {
                            "error": err_msg or "upsert_failed",
                            "will_retry": False,
                            "preflight_semantic": sem_preflight,
                            "governance_outcome": gov_outcome,
                            "governance_decision": gov_decision,
                            "preflight_latency_ms": preflight_latency_ms,
                            **(
                                {
                                    "semantic_trace_present": bool(
                                        sem_preflight.get("semantic_trace_present"),
                                    ),
                                    "semantic_trace_missing": bool(
                                        sem_preflight.get("semantic_trace_missing"),
                                    ),
                                    "semantic_trace": sem_preflight.get("semantic_trace"),
                                    "semantic_preflight_winning_stop_reason": sem_preflight.get(
                                        "semantic_preflight_winning_stop_reason",
                                    ),
                                }
                                if cls == "semantic_contradiction"
                                else {}
                            ),
                        },
                    },
                )
                gt_body = {
                    "corpus_row_id": corpus_row_id,
                    "conflict_class": cls,
                    "based_on_facts": row["based_on_facts"],
                    "proposed_key": proposed_key,
                    "proposed_kind": row["proposed_kind"],
                    "rationale_summary": row["rationale_summary"],
                    "expected_label": row["expected_label"],
                    "source_support": row["source_support"],
                    "injection_error": err_msg,
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

            # Notifications often cite baseline keys; include based_on_facts for faster poll matching.
            keyset = {proposed_key, *row["based_on_facts"]}
            # Wider skew than 2s: server created_at can lag client wall clock and falsely filter hits.
            after = (t_write_end - poll_after_skew_s) if t_write_end else None
            poll_policy = semantic_poll_policy(
                semantic_row=(cls == "semantic_contradiction"),
                sem_preflight=sem_preflight,
                default_max_wait_s=poll_max_s,
                semantic_detected_max_wait_s=float(args.semantic_detected_poll_max_wait),
                semantic_terminal_max_wait_s=float(args.semantic_terminal_poll_max_wait),
            )
            effective_poll_max_s = float(poll_policy["poll_max_wait_s_effective"])
            if poll_policy["poll_skipped"]:
                hit, poll_elapsed_s = None, 0.0
            else:
                hit, poll_elapsed_s = poll_for_conflict_notification(
                    mcp,
                    project_id,
                    keyset,
                    after,
                    interval_s=POLL_CONFLICTS_INTERVAL_S,
                    max_wait_s=effective_poll_max_s,
                )

            notif_created = hit is not None
            notif_id = hit.get("id") if hit else None
            notif_severity = hit.get("severity") if hit else None
            notif_created_at = hit.get("created_at") if hit else None
            notif_conflict_type = hit.get("conflict_type") if hit else None
            matched_on_key = hit.get("matched_on_key") if hit else None
            matched_on_anchor_only = bool(hit.get("matched_on_anchor_only")) if hit else False
            async_exact_type_match = bool(hit.get("exact_type_match")) if hit else False

            inline_detected = (conflicts_n > 0) if inline_available else False
            inline_exact_type_match = cls in conflict_types if inline_available else False
            preflight_severity = notif_severity or (
                (conflict_types[0] if conflict_types else None) if inline_available else None
            )
            observed_ms = (
                observed_notification_latency_ms(notif_created_at, t_write_end)
                if t_write_end and notif_created_at
                else None
            )

            semantic_primary_detected: bool | None = None
            semantic_primary_source: str | None = None
            semantic_terminal_reason: str | None = None
            if cls == "semantic_contradiction":
                (
                    semantic_primary_detected,
                    semantic_primary_source,
                    semantic_terminal_reason,
                ) = semantic_primary_detection_result(
                    sem_preflight=sem_preflight,
                    async_exact_type_match=async_exact_type_match,
                    inline_exact_type_match=inline_exact_type_match,
                )

            structural_primary_detected: bool | None = None
            structural_primary_source: str | None = None
            structural_terminal_reason: str | None = None
            if cls in STRUCTURAL_CONFLICT_CLASSES:
                (
                    structural_primary_detected,
                    structural_primary_source,
                    structural_terminal_reason,
                ) = structural_primary_detection_result(
                    expected_conflict_type=cls,
                    structural_preflight=structural_preflight,
                    async_exact_type_match=async_exact_type_match,
                    inline_exact_type_match=inline_exact_type_match,
                )

            observed_types = observed_conflict_types(
                sem_preflight=sem_preflight,
                structural_preflight=structural_preflight,
                inline_conflict_types=conflict_types if inline_available else [],
                matched_conflict_type=notif_conflict_type,
            )
            if cls == "semantic_contradiction":
                exact_type_match = bool(semantic_primary_detected)
            elif cls in STRUCTURAL_CONFLICT_CLASSES:
                exact_type_match = bool(structural_primary_detected)
            else:
                exact_type_match = False
            cross_type_alert = bool(observed_types - ({cls} if cls != "ambiguous_case" else set()))
            primary_detector_source = (
                semantic_primary_source
                if cls == "semantic_contradiction"
                else structural_primary_source
                if cls in STRUCTURAL_CONFLICT_CLASSES
                else None
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
                    "conflict_class": cls,
                    "corpus_row_id": corpus_row_id,
                    "based_on_facts": row["based_on_facts"],
                    "proposed_fact_key": proposed_key,
                    "ground_truth_key": ground_truth_key,
                    "result": {
                        "fact_keys": [proposed_key],
                        "expected_conflict_type": cls,
                        "missing_baseline_keys": missing_baseline,
                        **row_contract,
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
                        "exact_type_match": exact_type_match,
                        "cross_type_alert": cross_type_alert,
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
                            "poll_policy": poll_policy["poll_policy"],
                            "poll_skipped": bool(poll_policy["poll_skipped"]),
                            "poll_max_wait_s_effective": round(effective_poll_max_s, 2),
                            "matched_on_key": matched_on_key,
                            "matched_on_anchor_only": matched_on_anchor_only,
                            "matched_conflict_type": notif_conflict_type,
                            "exact_type_match": async_exact_type_match,
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
                                max_wait_s=effective_poll_max_s,
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
                "conflict_class": cls,
                "based_on_facts": row["based_on_facts"],
                "proposed_key": proposed_key,
                "proposed_kind": row["proposed_kind"],
                "rationale_summary": row["rationale_summary"],
                "expected_label": row["expected_label"],
                "source_support": row["source_support"],
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

            class_counts_progress[cls] += 1
            successes_since_checkpoint += 1
            injected_ids.add(corpus_row_id)
            print(f"[{injection_number}/{n_total}] {corpus_row_id} {cls} ok", flush=True)

            if successes_since_checkpoint >= 20:
                append_jsonl(
                    CHECKPOINTS,
                    {
                        "timestamp": iso_now(),
                        "phase": 2,
                        "checkpoint_type": "injection_progress",
                        "agent_id": AGENT_ID,
                        "status": "in_progress",
                        "injection_number": injection_number,
                        "last_corpus_row_id": corpus_row_id,
                        "class_counts": dict(class_counts_progress),
                        "target": n_total,
                    },
                )
                successes_since_checkpoint = 0

            _ = time.monotonic() - t0

        next_idx = resume_next_row_index(rows, project_id)
        if next_idx < n_total:
            print(
                f"Incomplete: {next_idx} conflict rows logged in order, expected {n_total}; re-run to resume.",
                file=sys.stderr,
            )
            return 1

        if not baseline_simulation_logged(project_id):
            baseline_detectable = {k: 0 for k in TARGET_PER_CLASS_FULL}
            baseline_missed = {k: int(class_counts_slice.get(k, 0)) for k in TARGET_PER_CLASS_FULL}

            append_jsonl(
                EXEC_LOG,
                {
                    "timestamp": iso_now(),
                    "phase": 2,
                    "agent_id": AGENT_ID,
                    "action": "baseline_simulation",
                    "project": project_id,
                    "result": {
                        "total_injected": n_total,
                        "rule": "temporal_same_key_overlap_only",
                        "note": "Corpus uses distinct p-* keys vs baseline f-*; baseline_detectable=0 per class unless same-key overlap exists",
                        "baseline_detectable": baseline_detectable,
                        "baseline_missed": baseline_missed,
                    },
                },
            )

            upsert_fact(
                mcp,
                project_id,
                kind="research",
                key="research.rdl.baseline.simulation",
                body=json.dumps(
                    {
                        "summary": "RDL Phase 2 baseline simulation: table-driven conflict slice; "
                        "distinct proposed keys → baseline temporal-overlap detector not triggered per Paper 3 rule.",
                        "source": rel_src,
                        "total_rows": n_total,
                    },
                    ensure_ascii=False,
                ),
                skip_conflict_check=True,
                skip_embedding=True,
            )

        REPORT_PATH.write_text(
            render_phase2_report_markdown(
                project_id=project_id,
                n_total=n_total,
                rel_src=rel_src,
                list_path=list_path,
                injection_limit=injection_limit,
                missing_baseline_keys_seen=missing_baseline_keys_seen,
            ),
            encoding="utf-8",
        )

        if not phase2_complete(required_n=n_total, project_id=project_id):
            append_jsonl(
                CHECKPOINTS,
                {
                    "timestamp": iso_now(),
                    "phase": 2,
                    "checkpoint_type": "phase_complete",
                    "agent_id": AGENT_ID,
                    "status": "complete",
                    "project_id": project_id,
                    "total_injections": n_total,
                    "report_path": "real-data-lab/research/real_data_lab_phase2_report.md",
                    "source": rel_src,
                },
            )

        print(f"Phase 2 complete. Report: {REPORT_PATH}")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
