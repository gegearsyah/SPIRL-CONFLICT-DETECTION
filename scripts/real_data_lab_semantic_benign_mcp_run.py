#!/usr/bin/env python3
"""
Real Data Lab — benign batch for semantic validation (list_benign_semantic_focus.md).

Runs after real_data_lab_semantic_conflict_mcp_run.py with the **same** --hoyer / --experiment-id.
Logs to the same per-experiment semantic execution log (phase 5).

See research_prompt/real_data_lab_semantic_validation_prompt.md.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Any

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from paper3_phase2_mcp_run import (  # noqa: E402
    McpSession,
    append_jsonl,
    detection_inline_available,
    iso_now,
    list_all_facts,
    load_json,
    observed_notification_latency_ms,
    parse_detection,
    poll_for_conflict_notification,
    POLL_CONFLICTS_INTERVAL_S,
)

from real_data_lab_phase2_mcp_run import (  # noqa: E402
    DEFAULT_SEMANTIC_DETECTED_POLL_MAX_WAIT_S,
    DEFAULT_SEMANTIC_TERMINAL_POLL_MAX_WAIT_S,
    build_semantic_preflight_block,
    corpus_key_token,
    load_project_id,
    memory_check_conflicts_v1,
    normalize_valid_ts,
    rdl_phase1_complete,
    semantic_poll_policy,
    semantic_primary_detection_result,
    upsert_fact,
)

from real_data_lab_semantic_conflict_mcp_run import semantic_conflict_complete  # noqa: E402

from real_data_lab_semantic_experiment import (  # noqa: E402
    add_semantic_experiment_cli,
    resolve_semantic_track,
    tag_log_row,
)

BTC_ROOT = _SCRIPTS.parent
REPO_ROOT = BTC_ROOT.parent
SPIRL_CONFIG = REPO_ROOT / ".spirl" / "config.json"
MCP_PATH = REPO_ROOT / ".cursor" / "mcp.json"
RDL = BTC_ROOT / "real-data-lab"
RESEARCH = RDL / "research"
DEFAULT_BENIGN_LIST = RDL / "list_benign_semantic_focus.md"

PHASE_CONFLICT = 4
PHASE_BENIGN = 5
AGENT_ID = "rdl_semantic_benign_agent"
SEMANTIC_POLL_MAX_S = 90.0

_ROW_RE = re.compile(
    r"^\|\s*(sb-[a-z]+-\d+)\s*\|\s*([^|]+)\|\s*(.+?)\s*\|\s*([^|]+)\|\s*(.+?)\s*\|\s*([^|]*?)\s*\|\s*$",
    re.I,
)
_KEY_RE = re.compile(r"\*\*Key:\*\*\s*(\S+)", re.I)
_CAT_RE = re.compile(r"\*\*Cat:\*\*\s*(\S+)", re.I)
_VAL_RE = re.compile(r"\*\*Val:\*\*\s*\"((?:[^\"\\]|\\.)*)\"", re.I)
_VALID_RE = re.compile(
    r"\*\*Valid:\*\*\s*(\S+)\s+(\S+)",
    re.I,
)

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


def semantic_benign_complete(checkpoints: Path) -> bool:
    if not checkpoints.exists():
        return False
    for line in checkpoints.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            o = json.loads(line)
        except json.JSONDecodeError:
            continue
        if o.get("checkpoint_type") == "semantic_benign_complete" and o.get("status") == "complete":
            return True
    return False


def benign_start_logged(exec_log: Path) -> bool:
    if not exec_log.exists():
        return False
    for line in exec_log.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            o = json.loads(line)
        except json.JSONDecodeError:
            continue
        if o.get("phase") == PHASE_BENIGN and o.get("action") == "benign_injection_start":
            return True
    return False


def resume_benign_index(exec_log: Path) -> int:
    n = 0
    if not exec_log.exists():
        return n
    for line in exec_log.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            o = json.loads(line)
        except json.JSONDecodeError:
            continue
        if o.get("phase") == PHASE_BENIGN and o.get("action") == "conflict_injected":
            if o.get("conflict_class") == "benign":
                n += 1
    return n


def parse_semantic_benign_table(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    text = path.read_text(encoding="utf-8")
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("| sb-"):
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
                "source_support": source_raw if source_raw else None,
            },
        )
    return rows


def result_detected(res: dict[str, Any]) -> bool:
    if "semantic_primary_detected" in res:
        return bool(res.get("semantic_primary_detected"))
    pre = res.get("preflight_check") or {}
    if pre.get("inline_detected"):
        return True
    async_o = res.get("async_observed") or {}
    if async_o.get("detected"):
        return True
    notif = res.get("notification") or {}
    if notif.get("created"):
        return True
    return False


def compute_semantic_validation_metrics(exec_log: Path) -> dict[str, Any]:
    tp = fn = fp = tn = 0
    if not exec_log.exists():
        return {
            "TP": 0,
            "FN": 0,
            "FP": 0,
            "TN": 0,
            "precision": 0.0,
            "recall": 0.0,
            "semantic_rows": 0,
            "benign_rows": 0,
        }

    for line in exec_log.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            o = json.loads(line)
        except json.JSONDecodeError:
            continue
        if o.get("action") != "conflict_injected":
            continue
        res = o.get("result") or {}
        det = result_detected(res)
        ph = o.get("phase")
        cls = o.get("conflict_class")
        if ph == PHASE_CONFLICT and cls == "semantic_contradiction":
            if det:
                tp += 1
            else:
                fn += 1
        elif ph == PHASE_BENIGN and cls == "benign":
            if det:
                fp += 1
            else:
                tn += 1

    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    return {
        "TP": tp,
        "FN": fn,
        "FP": fp,
        "TN": tn,
        "precision": prec,
        "recall": rec,
        "semantic_rows": tp + fn,
        "benign_rows": fp + tn,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="RDL semantic-validation benign batch via MCP")
    add_semantic_experiment_cli(ap)
    ap.add_argument("--limit", type=int, default=None, metavar="N", help="First N benign rows only")
    ap.add_argument(
        "--poll-max-wait",
        type=float,
        default=SEMANTIC_POLL_MAX_S,
        metavar="SEC",
        help="Max seconds to poll per row when semantic preflight is unavailable (default 90)",
    )
    ap.add_argument(
        "--semantic-terminal-poll-max-wait",
        type=float,
        default=DEFAULT_SEMANTIC_TERMINAL_POLL_MAX_WAIT_S,
        metavar="SEC",
        help="Effective async poll budget for terminal semantic preflight misses (default 0)",
    )
    ap.add_argument(
        "--semantic-detected-poll-max-wait",
        type=float,
        default=DEFAULT_SEMANTIC_DETECTED_POLL_MAX_WAIT_S,
        metavar="SEC",
        help="Effective async poll budget for semantic rows already detected in preflight (default 15)",
    )
    args = ap.parse_args()

    cfg = load_json(SPIRL_CONFIG)
    paths, experiment = resolve_semantic_track(
        RESEARCH,
        cfg,
        experiment_id_cli=(args.experiment_id or "").strip() or None,
        hoyer_lambda_cli=args.hoyer_lambda,
    )

    if semantic_benign_complete(paths.checkpoints):
        m = compute_semantic_validation_metrics(paths.execution_log)
        paths.validation_report.write_text(
            _format_report(m, cfg, paths, experiment, skipped_run=True),
            encoding="utf-8",
        )
        print(
            f"Semantic benign already complete for `{paths.experiment_id}`. Metrics: {paths.validation_report}",
        )
        return 0

    if not semantic_conflict_complete(paths.checkpoints):
        raise SystemExit(
            "Semantic conflict track not complete for this experiment; run "
            "real_data_lab_semantic_conflict_mcp_run.py with the same --hoyer / --experiment-id first.",
        )

    if not rdl_phase1_complete():
        raise SystemExit("Phase 1 not complete.")

    list_path = DEFAULT_BENIGN_LIST
    override = (cfg.get("real_data_lab_semantic_benign_list_path") or "").strip()
    if override:
        list_path = (BTC_ROOT / override).resolve() if not Path(override).is_absolute() else Path(override)

    rows = parse_semantic_benign_table(list_path)
    if not rows:
        raise SystemExit(f"No rows parsed from {list_path}")

    n_total = len(rows) if args.limit is None else min(len(rows), args.limit)
    rows = rows[:n_total]
    project_id = load_project_id(cfg)

    mcp_cfg = load_json(MCP_PATH)
    srv = mcp_cfg["mcpServers"]["spirl"]
    mcp = McpSession(srv["url"], srv["headers"]["Authorization"])
    mcp.connect()

    fact_keys_set = {str(f.get("key")) for f in list_all_facts(mcp, project_id) if f.get("key")}
    start_idx = resume_benign_index(paths.execution_log)

    def log(row: dict[str, Any]) -> dict[str, Any]:
        return tag_log_row(experiment, row)

    if not benign_start_logged(paths.execution_log):
        append_jsonl(
            paths.execution_log,
            log(
                {
                    "timestamp": iso_now(),
                    "phase": PHASE_BENIGN,
                    "agent_id": AGENT_ID,
                    "action": "benign_injection_start",
                    "project": project_id,
                    "result": {
                        "source": str(list_path.relative_to(BTC_ROOT)).replace("\\", "/")
                        if BTC_ROOT in list_path.parents or list_path == BTC_ROOT
                        else str(list_path),
                        "mode": "semantic_validation_benign",
                        "target_total": n_total,
                        "poll_max_wait_s": args.poll_max_wait,
                        "semantic_terminal_poll_max_wait_s": float(args.semantic_terminal_poll_max_wait),
                        "semantic_detected_poll_max_wait_s": float(args.semantic_detected_poll_max_wait),
                        "experiment_id": paths.experiment_id,
                    },
                },
            ),
        )

    injection_failed_rows: list[str] = []
    missing_baseline_keys_seen: set[str] = set()

    for i in range(start_idx, n_total):
        row = rows[i]
        injection_number = i + 1
        corpus_row_id = row["corpus_row_id"]
        proposed_key = row["proposed_key"]
        ground_truth_key = f"research.rdl.semantic_gt.{corpus_key_token(corpus_row_id)}"

        missing_baseline = [k for k in row["based_on_facts"] if k not in fact_keys_set]
        for mk in missing_baseline:
            missing_baseline_keys_seen.add(mk)

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
            )
        except Exception as e:
            preflight_err = str(e)
        sem_preflight = build_semantic_preflight_block(
            conflict_class="benign",
            preflight_raw=preflight_raw,
            preflight_error=preflight_err,
            semantic_track=True,
        )

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
                paths.execution_log,
                log(
                    {
                        "timestamp": iso_now(),
                        "phase": PHASE_BENIGN,
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
                            "preflight_semantic": sem_preflight,
                            "semantic_trace_present": bool(sem_preflight.get("semantic_trace_present")),
                            "semantic_trace_missing": bool(sem_preflight.get("semantic_trace_missing")),
                            "semantic_trace": sem_preflight.get("semantic_trace"),
                            "semantic_preflight_winning_stop_reason": sem_preflight.get(
                                "semantic_preflight_winning_stop_reason",
                            ),
                            "semantic_preflight_first_candidate_stop_reason": sem_preflight.get(
                                "semantic_preflight_first_candidate_stop_reason",
                            ),
                        },
                    },
                ),
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
        poll_policy = semantic_poll_policy(
            semantic_row=True,
            sem_preflight=sem_preflight,
            default_max_wait_s=float(args.poll_max_wait),
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

        inline_detected = (conflicts_n > 0) if inline_available else False
        preflight_severity = notif_severity or (
            (conflict_types[0] if conflict_types else None) if inline_available else None
        )
        observed_ms = (
            observed_notification_latency_ms(notif_created_at, t_write_end)
            if t_write_end and notif_created_at
            else None
        )
        semantic_primary_detected, semantic_primary_source, semantic_terminal_reason = semantic_primary_detection_result(
            sem_preflight=sem_preflight,
            async_detected=notif_created,
            inline_detected=inline_detected,
        )

        append_jsonl(
            paths.execution_log,
            log(
                {
                    "timestamp": iso_now(),
                    "phase": PHASE_BENIGN,
                    "agent_id": AGENT_ID,
                    "action": "conflict_injected",
                    "project": project_id,
                    "injection_number": injection_number,
                    "conflict_class": "benign",
                    "proposal_gold": "benign",
                    "gold_should_alert": False,
                    "corpus_row_id": corpus_row_id,
                    "based_on_facts": row["based_on_facts"],
                    "proposed_fact_key": proposed_key,
                    "ground_truth_key": ground_truth_key,
                    "result": {
                        "fact_keys": [proposed_key],
                        "missing_baseline_keys": missing_baseline,
                        "preflight_semantic": sem_preflight,
                        "semantic_trace_present": bool(sem_preflight.get("semantic_trace_present")),
                        "semantic_trace_missing": bool(sem_preflight.get("semantic_trace_missing")),
                        "semantic_trace": sem_preflight.get("semantic_trace"),
                        "semantic_preflight_winning_stop_reason": sem_preflight.get(
                            "semantic_preflight_winning_stop_reason",
                        ),
                        "semantic_preflight_first_candidate_stop_reason": sem_preflight.get(
                            "semantic_preflight_first_candidate_stop_reason",
                        ),
                        "semantic_primary_detected": semantic_primary_detected,
                        "semantic_primary_source": semantic_primary_source,
                        "semantic_terminal_stop_reason": semantic_terminal_reason,
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
                        },
                        "notification": {
                            "created": notif_created,
                            "notification_id": notif_id,
                            "conflict_type": notif_conflict_type,
                            "severity": notif_severity,
                            "created_at": notif_created_at,
                        },
                        "ground_truth_key": ground_truth_key,
                        "detection_latency_ms": det_lat,
                        "success": True,
                    },
                },
            ),
        )

        gt_body = {
            "track": "semantic_validation",
            "experiment_id": paths.experiment_id,
            "corpus_row_id": corpus_row_id,
            "conflict_class": "benign",
            "based_on_facts": row["based_on_facts"],
            "proposed_key": proposed_key,
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

        print(
            f"[semantic benign exp={paths.experiment_id} {injection_number}/{n_total}] {corpus_row_id} ok",
            flush=True,
        )

    done = resume_benign_index(paths.execution_log)
    if done < n_total:
        print(f"Incomplete: {done}/{n_total} benign rows logged.", file=sys.stderr)
        return 1

    m = compute_semantic_validation_metrics(paths.execution_log)
    paths.validation_report.write_text(
        _format_report(m, cfg, paths, experiment, skipped_run=False),
        encoding="utf-8",
    )

    append_jsonl(
        paths.execution_log,
        log(
            {
                "timestamp": iso_now(),
                "phase": PHASE_BENIGN,
                "agent_id": AGENT_ID,
                "action": "semantic_validation_metrics",
                "project": project_id,
                "result": {
                    "TP": m["TP"],
                    "FN": m["FN"],
                    "FP": m["FP"],
                    "TN": m["TN"],
                    "precision": m["precision"],
                    "recall": m["recall"],
                    "detection_rule": "semantic_primary_detected when present; otherwise inline_detected OR async_observed.detected OR notification.created",
                    "experiment_id": paths.experiment_id,
                },
            },
        ),
    )

    rel_val = paths.validation_report.relative_to(BTC_ROOT)
    append_jsonl(
        paths.checkpoints,
        log(
            {
                "timestamp": iso_now(),
                "phase": PHASE_BENIGN,
                "checkpoint_type": "semantic_benign_complete",
                "agent_id": AGENT_ID,
                "status": "complete",
                "total_benign_injections": n_total,
                "report_path": str(rel_val).replace("\\", "/"),
            },
        ),
    )

    print(f"Semantic validation complete. experiment_id={paths.experiment_id} Report: {paths.validation_report}")
    return 0


def _format_report(
    m: dict[str, Any],
    cfg: dict[str, Any],
    paths: Any,
    experiment: dict[str, Any],
    *,
    skipped_run: bool,
) -> str:
    pid = cfg.get("real_data_lab_project_id") or ""
    try:
        rel_log = paths.execution_log.relative_to(BTC_ROOT)
    except ValueError:
        rel_log = paths.execution_log
    exp_lines = [f"- **experiment_id:** `{paths.experiment_id}`"]
    if experiment.get("hoyer_lambda") is not None:
        exp_lines.append(
            f"- **Hoyer λ (provenance tag; configure on Spirl):** `{experiment['hoyer_lambda']}`",
        )
    lines = [
        "# Semantic validation report (contradiction + benign)",
        "",
        f"Generated: {iso_now()}",
        "",
        f"Project: `{pid}`",
        "",
        *exp_lines,
        "",
        "## Corpus",
        "",
        "- **Positives:** `list_conflict_semantic_only.md` (40 × `semantic_contradiction`), phase **4** in this experiment’s log.",
        "- **Negatives:** `list_benign_semantic_focus.md`, phase **5**.",
        "",
        f"- **This run’s log:** `{rel_log.as_posix()}`",
        "",
    ]
    lines.extend(
        [
            "## Pooled binary metrics",
            "",
            "Positive = semantic contradiction injection (**should alert**). Negative = benign injection (**should not alert**).",
            "",
            "| Metric | Count / value |",
            "|--------|---------------:|",
            f"| TP (semantic, detected) | {m['TP']} |",
            f"| FN (semantic, missed) | {m['FN']} |",
            f"| FP (benign, alerted) | {m['FP']} |",
            f"| TN (benign, clean) | {m['TN']} |",
            f"| Precision TP/(TP+FP) | {m['precision']:.4f} |",
            f"| Recall TP/(TP+FN) | {m['recall']:.4f} |",
            "",
            "_Detection rule (injection-level): semantic rows score `semantic_primary_detected` first; async notification remains transport evidence and inline detection is only fallback when semantic trace is unavailable._",
            "",
        ]
    )
    if skipped_run:
        lines.append("_Report regenerated from existing log (benign batch was already complete)._")
        lines.append("")
    lines.extend(
        [
            "## Artifacts",
            "",
            f"- `{paths.execution_log.name}`",
            f"- `{paths.checkpoints.name}`",
            "",
        ]
    )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
