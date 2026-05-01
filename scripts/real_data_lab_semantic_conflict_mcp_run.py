#!/usr/bin/env python3
"""
Real Data Lab — semantic-contradiction-only conflict injections (40 rows).

Uses list_conflict_semantic_only.md, separate logs from full Phase 2.
Poll window defaults to 90s per row (async NLI / embedding).

Reuse for sweeps (e.g. Hoyer 0.10 / 0.15 / 0.25; lab standard λ = 0.25) via --hoyer and/or --experiment-id;
each experiment writes its own JSONL + reports.

See research_prompt/real_data_lab_semantic_validation_prompt.md.
"""
from __future__ import annotations

import argparse
import json
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
    parse_conflict_table,
    rdl_phase1_complete,
    semantic_poll_policy,
    semantic_primary_detection_result,
    upsert_fact,
)

from real_data_lab_semantic_experiment import (  # noqa: E402
    SemanticTrackPaths,
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
DEFAULT_LIST = RDL / "list_conflict_semantic_only.md"

PHASE = 4
AGENT_ID = "rdl_semantic_conflict_agent"
SEMANTIC_POLL_MAX_S = 90.0


def semantic_conflict_complete(checkpoints: Path, phase: int = PHASE) -> bool:
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
        if o.get("phase") == phase and o.get("checkpoint_type") == "phase_complete" and o.get("status") == "complete":
            return True
    return False


def conflict_injection_start_logged(exec_log: Path, phase: int = PHASE) -> bool:
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
        if o.get("phase") == phase and o.get("action") == "conflict_injection_start":
            return True
    return False


def resume_next_row_index(exec_log: Path, phase: int = PHASE) -> int:
    last = 0
    if not exec_log.exists():
        return last
    for line in exec_log.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            o = json.loads(line)
        except json.JSONDecodeError:
            continue
        if o.get("phase") != phase or o.get("action") != "conflict_injected":
            continue
        n = int(o.get("injection_number") or 0)
        last = max(last, n)
    return last


def summary_logged(exec_log: Path, phase: int = PHASE) -> bool:
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
        if o.get("phase") == phase and o.get("action") == "semantic_track_summary":
            return True
    return False


def main() -> int:
    ap = argparse.ArgumentParser(description="RDL semantic-only conflict injections via MCP")
    add_semantic_experiment_cli(ap)
    ap.add_argument("--injection-limit", type=int, default=None, metavar="N", help="First N rows only")
    ap.add_argument(
        "--poll-max-wait",
        type=float,
        default=SEMANTIC_POLL_MAX_S,
        metavar="SEC",
        help="Max seconds to poll for async conflict notification per row when semantic preflight is unavailable (default 90)",
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

    list_path = DEFAULT_LIST
    override = (cfg.get("real_data_lab_semantic_conflict_list_path") or "").strip()
    if override:
        list_path = (BTC_ROOT / override).resolve() if not Path(override).is_absolute() else Path(override)

    injection_limit = args.injection_limit
    if injection_limit is None:
        lim = cfg.get("real_data_lab_semantic_injection_limit")
        if lim is not None:
            try:
                injection_limit = int(lim)
                if injection_limit <= 0:
                    injection_limit = None
            except (TypeError, ValueError):
                injection_limit = None

    if semantic_conflict_complete(paths.checkpoints):
        print(f"Semantic conflict track already complete for experiment `{paths.experiment_id}`. Exiting.")
        return 0

    if not rdl_phase1_complete():
        raise SystemExit("Phase 1 not complete (real_data_lab_checkpoints.jsonl).")

    rows = parse_conflict_table(list_path)
    for row in rows:
        if row["conflict_class"] != "semantic_contradiction":
            raise SystemExit(f"Non-semantic row in {list_path}: {row.get('corpus_row_id')}")

    if not rows:
        raise SystemExit(f"No rows parsed from {list_path}")

    n_total = len(rows) if injection_limit is None else min(len(rows), injection_limit)
    rows = rows[:n_total]
    project_id = load_project_id(cfg)

    mcp_cfg = load_json(MCP_PATH)
    srv = mcp_cfg["mcpServers"]["spirl"]
    mcp = McpSession(srv["url"], srv["headers"]["Authorization"])
    mcp.connect()

    fact_keys_set = {str(f.get("key")) for f in list_all_facts(mcp, project_id) if f.get("key")}
    start_idx = resume_next_row_index(paths.execution_log)

    paths.execution_log.parent.mkdir(parents=True, exist_ok=True)

    def log(row: dict[str, Any]) -> dict[str, Any]:
        return tag_log_row(experiment, row)

    if not conflict_injection_start_logged(paths.execution_log):
        append_jsonl(
            paths.checkpoints,
            log(
                {
                    "timestamp": iso_now(),
                    "phase": PHASE,
                    "checkpoint_type": "phase_start",
                    "agent_id": AGENT_ID,
                    "status": "in_progress",
                    "notes": f"Semantic-only conflict injections (c-sem-*), experiment_id={paths.experiment_id}",
                },
            ),
        )
        append_jsonl(
            paths.execution_log,
            log(
                {
                    "timestamp": iso_now(),
                    "phase": PHASE,
                    "agent_id": AGENT_ID,
                    "action": "conflict_injection_start",
                    "project": project_id,
                    "result": {
                        "source": str(list_path.relative_to(BTC_ROOT)).replace("\\", "/")
                        if BTC_ROOT in list_path.parents or list_path == BTC_ROOT
                        else str(list_path),
                        "mode": "semantic_contradiction_only",
                        "target_total": n_total,
                        "target_per_class": {"semantic_contradiction": n_total},
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
        cls = row["conflict_class"]
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
            conflict_class=cls,
            preflight_raw=preflight_raw,
            preflight_error=preflight_err,
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
                        "phase": PHASE,
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
            gt_body = {
                "track": "semantic_validation",
                "experiment_id": paths.experiment_id,
                "corpus_row_id": corpus_row_id,
                "conflict_class": cls,
                "based_on_facts": row["based_on_facts"],
                "proposed_key": proposed_key,
                "gold_should_alert": True,
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
                    "phase": PHASE,
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
                        "gold_should_alert": True,
                        "success": True,
                    },
                },
            ),
        )

        gt_body = {
            "track": "semantic_validation",
            "experiment_id": paths.experiment_id,
            "corpus_row_id": corpus_row_id,
            "conflict_class": cls,
            "based_on_facts": row["based_on_facts"],
            "proposed_key": proposed_key,
            "proposed_kind": row["proposed_kind"],
            "gold_should_alert": True,
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
            f"[semantic exp={paths.experiment_id} {injection_number}/{n_total}] {corpus_row_id} ok",
            flush=True,
        )

    done = resume_next_row_index(paths.execution_log)
    if done < n_total:
        print(
            f"Incomplete: {done}/{n_total} semantic conflict_injected lines; fix and re-run.",
            file=sys.stderr,
        )
        return 1

    if not summary_logged(paths.execution_log):
        append_jsonl(
            paths.execution_log,
            log(
                {
                    "timestamp": iso_now(),
                    "phase": PHASE,
                    "agent_id": AGENT_ID,
                    "action": "semantic_track_summary",
                    "project": project_id,
                    "result": {
                        "note": "Semantic contradiction injections complete; run real_data_lab_semantic_benign_mcp_run.py with the same --hoyer / --experiment-id.",
                        "rows": n_total,
                        "ground_truth_prefix": "research.rdl.semantic_gt.*",
                        "experiment_id": paths.experiment_id,
                    },
                },
            ),
        )

    inj = fail = 0
    if paths.execution_log.exists():
        for line in paths.execution_log.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                o = json.loads(line)
            except json.JSONDecodeError:
                continue
            if o.get("phase") != PHASE or o.get("conflict_class") != "semantic_contradiction":
                continue
            if o.get("action") == "conflict_injected":
                inj += 1
            elif o.get("action") == "injection_failed":
                fail += 1

    exp_md = ""
    if experiment.get("hoyer_lambda") is not None:
        exp_md = f"- **Hoyer λ (tag only; set on Spirl server):** `{experiment['hoyer_lambda']}`\n"
    exp_md += f"- **experiment_id:** `{paths.experiment_id}`\n"

    rel_log = paths.execution_log.relative_to(BTC_ROOT)
    rel_cp = paths.checkpoints.relative_to(BTC_ROOT)
    paths.conflict_report.write_text(
        "\n".join(
            [
                "# Semantic conflict track — injection report",
                "",
                f"Generated: {iso_now()}",
                "",
                exp_md,
                f"- Project: `{project_id}`",
                f"- Source: `{list_path}`",
                f"- Rows: **{n_total}** (`semantic_contradiction` only)",
                f"- Logged injected: **{inj}**, failed: **{fail}**",
                "",
                "Ground truth facts use prefix **`research.rdl.semantic_gt.*`** (distinct from full Phase 2 `research.rdl.groundtruth.*`).",
                "",
                "## Artifacts",
                "",
                f"- `{rel_log}`",
                f"- `{rel_cp}`",
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    rel_rep = paths.conflict_report.relative_to(BTC_ROOT)
    if not semantic_conflict_complete(paths.checkpoints):
        append_jsonl(
            paths.checkpoints,
            log(
                {
                    "timestamp": iso_now(),
                    "phase": PHASE,
                    "checkpoint_type": "phase_complete",
                    "agent_id": AGENT_ID,
                    "status": "complete",
                    "total_injections": n_total,
                    "report_path": str(rel_rep).replace("\\", "/"),
                },
            ),
        )

    print(f"Semantic conflict track complete. experiment_id={paths.experiment_id} Report: {paths.conflict_report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
