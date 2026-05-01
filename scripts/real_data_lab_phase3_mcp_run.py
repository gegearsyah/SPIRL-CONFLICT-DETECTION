#!/usr/bin/env python3
"""
Real Data Lab Phase 3 — score from execution log, write phase 3 report, optional RQ upserts via MCP.

Expects Phase 2 + 2b complete (benign script may have already appended mixed metric_computed lines).
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from argparse import Namespace
from pathlib import Path
from typing import Any

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from paper3_phase2_mcp_run import McpSession, append_jsonl, iso_now, load_json
from paper3_paths import btc_root, mcp_json_path, spirl_config_path
from real_data_lab_benign_mcp_run import compute_mixed_metrics_from_log, collect_error_analysis_from_log
from real_data_lab_phase2_mcp_run import (
    EXEC_LOG,
    CHECKPOINTS,
    load_project_id,
    phase2_complete,
    effective_conflict_injection_total,
    resolve_conflict_list_path,
)
from rdl_pipeline_execution_lock import rdl_pipeline_lock

RESEARCH = btc_root() / "real-data-lab" / "research"
REPORT_PATH = RESEARCH / "real_data_lab_phase3_report.md"
CONTRACT_AUDIT_PATH = RESEARCH / "real_data_lab_contract_audit.md"
CONFUSION_MATRIX_PATH = RESEARCH / "real_data_lab_confusion_matrix.md"
ERROR_ANALYSIS_PATH = RESEARCH / "real_data_lab_error_analysis.jsonl"
CONFIG_PATH = spirl_config_path()
MCP_PATH = mcp_json_path()
AGENT = "rdl_phase3_judge_agent"


def per_class_from_log(path: Path) -> dict[str, dict[str, int]]:
    metrics = compute_mixed_metrics_from_log()
    return metrics.get("by_class", {})


def f1_from_pr(p: float, r: float) -> float:
    if p + r <= 0:
        return 0.0
    return 2.0 * p * r / (p + r)


def phase3_complete_checkpoint_exists() -> bool:
    if not CHECKPOINTS.is_file():
        return False
    for line in CHECKPOINTS.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            o = json.loads(line)
        except json.JSONDecodeError:
            continue
        if o.get("phase") == 3 and o.get("checkpoint_type") == "phase_complete" and o.get("status") == "complete":
            return True
    return False


def upsert_rq_facts(
    mcp: McpSession,
    project_id: str,
    *,
    n_conflict: int,
    m: dict[str, Any],
    arch_label: str,
    arch_doc: str,
) -> None:
    def _body(text: str) -> str:
        return json.dumps(
            {
                "summary": text,
                "corpus_conflicts": n_conflict,
                "architecture_label": arch_label,
                "architecture_doc": arch_doc,
            },
            ensure_ascii=False,
        )

    rq1 = (
        f"RQ1 (detection coverage): On {n_conflict} table-driven conflict injections, "
        f"recall (any alert) = {m.get('pooled_recall', 0):.4f} over conflict rows; "
        f"per-class breakdown is in the Phase 3 report."
    )
    rq2 = (
        f"RQ2 (benign false alerts): FP rate on benign rows = {m.get('benign_fp_rate', 0):.4f} "
        f"({m.get('benign_fp', 0)} FP / {m.get('benign_total', 0)} benign)."
    )
    rq3 = (
        f"RQ3 (pooled policy): Precision = {m.get('pooled_precision', 0):.4f}, "
        f"Recall = {m.get('pooled_recall', 0):.4f} on binary alert-warranted (conflict=positive, benign=negative). "
        f"Staged pipeline label: {arch_label}."
    )
    for key, body in (
        ("research.rdl.results.rq1", rq1),
        ("research.rdl.results.rq2", rq2),
        ("research.rdl.results.rq3", rq3),
    ):
        mcp.call_tool(
            "memory_upsert_fact_v1",
            {
                "project_id": project_id,
                "kind": "research",
                "key": key,
                "body": _body(body),
                "tier": 1,
                "source_type": "human",
                "actor": AGENT,
                "agent_id": AGENT,
                "skip_conflict_check": True,
                "skip_embedding": True,
            },
        )
        append_jsonl(
            EXEC_LOG,
            {
                "timestamp": iso_now(),
                "phase": 3,
                "agent_id": AGENT,
                "action": "rq_answer_written",
                "project": project_id,
                "result": {"fact_key": key},
            },
        )



def write_phase3_report(
    path: Path,
    project_id: str,
    cfg: dict,
    by_class: dict[str, dict[str, int]],
    m: dict[str, Any],
) -> None:
    arch = str(cfg.get("real_data_lab_architecture_label") or "")
    doc = str(cfg.get("real_data_lab_architecture_doc") or "")
    report_status = str(m.get("report_status") or "diagnostic_only")
    confusion = m.get("exact_confusion") or {}
    benign_fp_by_detector = m.get("benign_fp_by_detector") or {}
    audit = m.get("contract_audit") or {}
    integrity_notes = m.get("report_integrity_notes") or []
    integrity_note_text = ", ".join(integrity_notes) if integrity_notes else "none"
    lines = [
        "# Phase 3 Report - Real Data Lab", "",
        f"Generated: {iso_now()}", "",
        f"- `project_id`: `{project_id}`",
        f"- Architecture label: `{arch}`",
        f"- Architecture doc: `{doc}`",
        f"- Report status: `{report_status}`", "",
        "## Mixed workload summary", "",
        "| Metric | Value |", "|--------|------:|",
        f"| Binary recall | {m.get('conflict_recall', 0):.4f} |",
        f"| Core-4 exact-type recall | {m.get('core4_exact_type_recall', 0):.4f} |",
        f"| All-row exact-type recall | {m.get('all_rows_exact_type_recall', 0):.4f} |",
        f"| Wrong-type alert rate | {m.get('wrong_type_alert_rate', 0):.4f} |",
        f"| Benign FP rate | {m.get('benign_fp_rate', 0):.4f} |",
        f"| Benign specificity | {m.get('benign_specificity', 0):.4f} |",
        f"| Preflight coverage | {m.get('preflight_coverage', 0):.4f} |",
        f"| Preflight unavailable rate | {m.get('preflight_unavailable_rate', 0):.4f} |",
        f"| Semantic trace coverage | {m.get('semantic_trace_coverage', 0):.4f} |",
        f"| Precision-safe mixed score | {m.get('precision_safe_mixed_score', 0):.4f} |", "",
        "## Governance outcome (Wave 4.3)", "",
        "Neyman-Pearson LLR selector (arXiv:2505.15008) promotes "
        "`governance_outcome` to a first-class preflight field and is "
        "scored here against the AbstentionBench (arXiv:2506.09038) "
        "protocol.", "",
        "| Metric | Value |", "|--------|------:|",
        f"| `needs_review` precision | {m.get('needs_review_precision', 0):.4f} |",
        f"| `needs_review` recall on ambiguous rows | {m.get('needs_review_recall_ambiguous', 0):.4f} |",
        f"| Unsafe forced-type rate (ambiguous) | {m.get('unsafe_forced_type_rate_ambiguous', 0):.4f} |",
        f"| Ambiguous rows routed to `needs_review` (TP) | {m.get('ambiguous_needs_review', 0)} |",
        f"| Benign rows routed to `needs_review` (FP) | {m.get('benign_needs_review', 0)} |",
        f"| Typed-conflict rows routed to `needs_review` (FN) | {m.get('conflict_needs_review', 0)} |",
        f"| Governance outcome counts | `{json.dumps(m.get('governance_outcome_counts') or {}, ensure_ascii=False)}` |", "",
        "## Benign diagnostics", "", "| Metric | Value |", "|--------|------:|",
        f"| Semantic benign FP | {m.get('semantic_benign_fp', 0)} |",
        f"| Constraint benign FP | {m.get('constraint_benign_fp', 0)} |",
        f"| Dependency benign FP | {m.get('dependency_benign_fp', 0)} |",
        f"| Semantic budget-exhausted benign count | {m.get('semantic_budget_exhausted_benign_count', 0)} |", "",
        "## Coherence / authority summary", "", "| Metric | Value |", "|--------|------:|",
        f"| Preflight-first detected | {m.get('preflight_first_detected', 0)} |",
        f"| Async-only recoveries | {m.get('async_stronger_than_preflight', 0)} |",
        f"| Preflight/async disagreements | {m.get('preflight_async_disagreement', 0)} |",
        f"| Winning plane counts | `{json.dumps(m.get('winning_plane_counts') or {}, ensure_ascii=False)}` |",
        f"| Detector-plane authority | `{m.get('detector_plane_authority', 'nested_preflight_authority_when_available')}` |", "",
        "## Report integrity", "", "| Field | Value |", "|-------|------:|",
        f"| Report integrity OK | `{m.get('report_integrity_ok', False)}` |",
        f"| Integrity notes | `{integrity_note_text}` |", "",
        "## Contract audit", "", "| Field | Value |", "|-------|------:|",
        f"| Rows scored | {audit.get('rows_scored', 0)} |",
        f"| Contract-complete rows | {audit.get('contract_complete_rows', 0)} |",
        f"| Contract-incomplete rows | {audit.get('contract_incomplete_rows', 0)} |",
        f"| Semantic trace missing | {audit.get('semantic_trace_missing_rows', 0)} |", "",
        "## Benign FP by detector", "", "| Detector | FP |", "|----------|---:|",
    ]
    if benign_fp_by_detector:
        for det, count in benign_fp_by_detector.items():
            lines.append(f"| `{det}` | {count} |")
    else:
        lines.append("| `none` | 0 |")
    lines.extend(["", "## Exact-type confusion matrix", "", "| Expected | semantic | dependency | constraint | temporal | none |", "|----------|---------:|-----------:|-----------:|---------:|-----:|"])
    for expected in ("semantic_contradiction", "dependency_impact", "constraint_violation", "temporal_invalidation"):
        row = confusion.get(expected, {})
        lines.append("| `{}` | {} | {} | {} | {} | {} |".format(expected, row.get("semantic_contradiction", 0), row.get("dependency_impact", 0), row.get("constraint_violation", 0), row.get("temporal_invalidation", 0), row.get("none", 0)))
    if report_status != "publishable":
        lines.extend(["", "This run is diagnostic-only because contract-critical fields were missing, semantic traces were incomplete, or report-integrity checks failed.", ""])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_contract_audit(path: Path, metrics: dict[str, Any]) -> None:
    audit = metrics.get("contract_audit") or {}
    lines = [
        "# Contract Audit", "",
        f"Generated: {iso_now()}",
        f"- Report status: `{metrics.get('report_status', 'diagnostic_only')}`",
        f"- Rows scored: `{audit.get('rows_scored', 0)}`",
        f"- Contract-complete rows: `{audit.get('contract_complete_rows', 0)}`",
        f"- Contract-incomplete rows: `{audit.get('contract_incomplete_rows', 0)}`",
        f"- Semantic trace missing: `{audit.get('semantic_trace_missing_rows', 0)}`", "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\\n".join(lines), encoding="utf-8")


def write_confusion_matrix(path: Path, metrics: dict[str, Any]) -> None:
    confusion = metrics.get("exact_confusion") or {}
    lines = [
        "# Exact-Type Confusion Matrix", "",
        f"Generated: {iso_now()}",
        "| Expected | semantic | dependency | constraint | temporal | none |",
        "|----------|---------:|-----------:|-----------:|---------:|-----:|",
    ]
    for expected in ("semantic_contradiction", "dependency_impact", "constraint_violation", "temporal_invalidation"):
        row = confusion.get(expected, {})
        lines.append("| `{}` | {} | {} | {} | {} | {} |".format(expected, row.get("semantic_contradiction", 0), row.get("dependency_impact", 0), row.get("constraint_violation", 0), row.get("temporal_invalidation", 0), row.get("none", 0)))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\\n".join(lines) + "\\n", encoding="utf-8")


def write_error_analysis(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\\n")


def main() -> int:
    ap = argparse.ArgumentParser(description="Real Data Lab Phase 3 — report + RQ from execution log")
    ap.add_argument("--no-upsert-rq", action="store_true", help="Skip MCP upserts for rq1–rq3")
    ap.add_argument("--force", action="store_true", help="Rewrite report even if phase 3 checkpoint exists")
    ap.add_argument(
        "--ignore-pipeline-lock",
        action="store_true",
        help="Skip real_data_lab_pipeline.lock (only if no other RDL script is writing the execution log).",
    )
    args = ap.parse_args()

    with rdl_pipeline_lock(ignore=bool(args.ignore_pipeline_lock)):
        return phase3_run(args)


def phase3_run(args: Namespace) -> int:
    cfg = load_json(CONFIG_PATH)
    project_id = load_project_id(cfg)
    conflict_list = resolve_conflict_list_path(cfg, None)
    need_n = effective_conflict_injection_total(cfg, conflict_list)
    if not phase2_complete(required_n=need_n, project_id=project_id):
        print("Phase 2 not complete for configured conflict slice.", file=sys.stderr)
        return 1

    m = compute_mixed_metrics_from_log()
    by_class = per_class_from_log(EXEC_LOG)
    error_rows = collect_error_analysis_from_log()
    write_phase3_report(REPORT_PATH, project_id, cfg, by_class, m)
    write_contract_audit(CONTRACT_AUDIT_PATH, m)
    write_confusion_matrix(CONFUSION_MATRIX_PATH, m)
    write_error_analysis(ERROR_ANALYSIS_PATH, error_rows)

    if str(m.get("report_status") or "diagnostic_only") != "publishable":
        print("Phase 3 is diagnostic-only because contract-critical fields or semantic traces were incomplete.", file=sys.stderr)
        return 1

    if phase3_complete_checkpoint_exists() and not args.force:
        print("Phase 3 already complete (checkpoint). Use --force to regenerate report.")
        return 0

    p, r = float(m.get("pooled_precision") or 0), float(m.get("pooled_recall") or 0)
    f1 = f1_from_pr(p, r)
    append_jsonl(EXEC_LOG, {"timestamp": iso_now(), "phase": 3, "agent_id": AGENT, "action": "metric_computed", "project": project_id, "metric_group": "cross_project_consistency", "result": {"overall_F1": f1, "precision_safe_mixed_score": m.get("precision_safe_mixed_score"), "corpus": "real_data_lab"}})

    if not args.no_upsert_rq:
        mcp_cfg = load_json(MCP_PATH)
        srv = mcp_cfg["mcpServers"]["spirl"]
        session = McpSession(srv["url"], srv["headers"]["Authorization"])
        session.connect()
        upsert_rq_facts(session, project_id, n_conflict=int(m.get("conflict_total") or 0), m=m, arch_label=str(cfg.get("real_data_lab_architecture_label") or ""), arch_doc=str(cfg.get("real_data_lab_architecture_doc") or ""))

    append_jsonl(CHECKPOINTS, {"timestamp": iso_now(), "phase": 3, "checkpoint_type": "phase_complete", "agent_id": AGENT, "status": "complete", "report_path": "real-data-lab/research/real_data_lab_phase3_report.md", "notes": "Automated Phase 3 from execution log + optional RQ upserts"})
    print("Phase 3 report:", REPORT_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
