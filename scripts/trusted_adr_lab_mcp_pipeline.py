#!/usr/bin/env python3
"""
Trusted ADR Lab (TAL) — consolidated MCP pipeline for phases 1, 2, 2b, 3.

The TAL phase entry scripts (``trusted_adr_lab_phase{1,2,2b,3}_mcp_run.py``)
are thin wrappers around the ``run_phase*`` functions in this module.  The
module mirrors the RDL pipeline contract (same log schema, same scoring
semantics) so the EMNLP companion tables can be produced with a single
scoring function + two domain-specific row sources.

Design notes:
  * Phase 1 imports 66 ADR facts from
    ``trusted-adr-lab/research/trusted_adr/adr_extracted_fact_manifest.jsonl``
    into a dedicated ``trusted_adr_lab`` project via MCP ``memory_upsert_fact_v1``
    with ``skip_conflict_check=True``.  Unlike RDL, there is no edge plan:
    ADR files are self-contained decisions, so the knowledge graph stays
    at the fact-level (no ``depends_on`` / ``implements`` edges).
  * Phases 2 & 2b inject the 8 / 4 / 6 rows from
    ``trusted_{conflict,ambiguity,benign}_rows.jsonl``.  Each injection runs
    ``memory_check_conflicts_v1`` first (preflight) then
    ``memory_upsert_fact_v1`` with conflict checking ON, logging the full
    envelope so Phase 3 can rescore without calling the server again.
  * Phase 3 uses a TAL-specific scorer that keys on the row_id prefix
    ``d-{sem,con,tmp,ben,amb}-*`` (TAL's material-ized convention) instead
    of the RDL ``{c-, b-, sb-}`` prefixes.  The scoring contract — pooled
    precision, core-4 exact-type recall, ``needs_review_precision``,
    ``unsafe_forced_type_rate_ambiguous`` — is identical to the RDL
    contract so both corpora can be compared in the same table.

References for the governance scoring split:
  * Heng & Soh, 2026 — Neyman-Pearson LLR selector (arXiv:2505.15008).
  * AbstentionBench, 2026 — abstention evaluation protocol
    (arXiv:2506.09038).
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from paper3_paths import mcp_json_path, spirl_config_path  # noqa: E402
from paper3_phase1_mcp_run import (  # noqa: E402
    McpSession,
    aggregate_facts,
    append_jsonl,
    iso_now,
    list_all_facts,
    load_json,
)
from real_data_lab_benign_mcp_run import (  # noqa: E402
    _GOV_NEEDS_REVIEW,
    _governance_outcome_from_result,
    _preflight_primary_prediction,
    build_structural_preflight_block,
    structural_primary_detection_result,
)
from real_data_lab_phase2_mcp_run import (  # noqa: E402
    build_semantic_preflight_block,
    detection_inline_available,
    memory_check_conflicts_v1,
    merge_row_contract_fields,
    observed_notification_latency_ms,
    parse_detection,
    poll_for_conflict_notification,
    semantic_preflight_detected,
    semantic_terminal_stop_reason,
)
from trusted_adr_lab_common import (  # noqa: E402
    TAL_AGENT_ID,
    TAL_PHASE1_AGENT,
    TAL_PHASE2B_AGENT,
    TAL_PHASE3_AGENT,
    TAL_SLUG,
    read_jsonl,
    tal_ambiguity_rows,
    tal_benign_rows,
    tal_checkpoints,
    tal_confusion_matrix,
    tal_conflict_rows,
    tal_exec_log,
    tal_expected_counts,
    tal_fact_manifest,
    tal_mixed_report,
    tal_phase1_report,
    tal_phase2_report,
    tal_phase3_report,
    tal_research_dir,
)


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------
def _spirl_cfg_path() -> Path:
    return spirl_config_path()


def _mcp_cfg_path() -> Path:
    return mcp_json_path()


def load_tal_project_id(cfg: dict[str, Any]) -> str:
    pid = (cfg.get("trusted_adr_lab_project_id") or "").strip()
    if pid:
        return pid
    p = cfg.get("projects") or {}
    v = p.get(f"{TAL_SLUG}_project") or p.get("trusted_adr_lab_project")
    if v:
        return str(v)
    raise SystemExit(
        "Set trusted_adr_lab_project_id in .spirl/config.json "
        "(or projects.trusted_adr_lab_project)."
    )


def _open_mcp() -> McpSession:
    mcp_cfg = load_json(_mcp_cfg_path())
    srv = mcp_cfg["mcpServers"]["spirl"]
    mcp = McpSession(srv["url"], srv["headers"]["Authorization"])
    mcp.connect()
    return mcp


# ---------------------------------------------------------------------------
# Phase 1 — corpus import
# ---------------------------------------------------------------------------
def _fact_body_from_manifest(rec: dict[str, Any]) -> str:
    """Derive a faithful fact body from the ADR manifest entry.

    The manifest records each ADR section (``Decision`` / ``Consequences`` /
    ``Status`` …) as its own fact with ``evidence_snippet`` as the
    source-verified text.  Using the snippet directly keeps the TAL
    baseline grounded in verbatim ADR content rather than summarizer noise.
    """
    snippet = str(rec.get("evidence_snippet") or "").strip()
    section = str(rec.get("source_section") or "").strip()
    if snippet:
        if section:
            return f"{section}: {snippet}"
        return snippet
    return str(rec.get("fact_key") or "")


def run_phase1(*, resume: bool = False) -> int:
    """Import the 66 ADR facts into the TAL project.

    Writes a ``baseline_snapshot`` + N ``fact_imported`` + ``graph_verified``
    trace to ``trusted_adr_lab_execution_log.jsonl`` and a human-readable
    report to ``trusted_adr_lab_phase1_report.md``.
    """
    research = tal_research_dir()
    research.mkdir(parents=True, exist_ok=True)
    manifest_path = tal_fact_manifest()
    if not manifest_path.is_file():
        raise SystemExit(
            f"Missing fact manifest: {manifest_path} — run "
            "scripts/experiment_d_trusted_adr_track.py first."
        )

    cfg = load_json(_spirl_cfg_path())
    project_id = load_tal_project_id(cfg)

    exec_log = tal_exec_log()
    checkpoints = tal_checkpoints()

    if not resume:
        exec_log.write_text("", encoding="utf-8")
        checkpoints.write_text("", encoding="utf-8")

    append_jsonl(
        checkpoints,
        {
            "timestamp": iso_now(),
            "phase": 1,
            "checkpoint_type": "phase_start" if not resume else "resume",
            "agent_id": TAL_PHASE1_AGENT,
            "project_id": project_id,
            "status": "in_progress",
            "notes": "Trusted ADR Lab Phase 1 — ADR fact import (external-validity corpus)",
        },
    )

    mcp = _open_mcp()
    mcp.call_tool("get_pm_context", {"project_id": project_id})

    facts_before = list_all_facts(mcp, project_id)
    by_kind, by_tier = aggregate_facts(facts_before)
    existing_keys = {str(f.get("key")) for f in facts_before if f.get("key")}

    # Resolve any pre-existing conflicts so the TAL baseline is clean.
    existing_conflicts = mcp.call_tool(
        "list_conflicts_v1",
        {"project_id": project_id, "limit": 200, "unresolved_only": True},
    )
    for c in existing_conflicts.get("conflicts") or []:
        cid = c.get("id") or c.get("conflict_id")
        if not cid:
            continue
        mcp.call_tool(
            "resolve_conflict_v1",
            {
                "project_id": project_id,
                "conflict_id": str(cid),
                "resolution": "accepted",
                "resolved_by": TAL_PHASE1_AGENT,
            },
        )

    append_jsonl(
        exec_log,
        {
            "timestamp": iso_now(),
            "phase": 1,
            "agent_id": TAL_PHASE1_AGENT,
            "action": "baseline_snapshot",
            "project": project_id,
            "result": {
                "total_facts": len(facts_before),
                "by_kind": by_kind,
                "by_tier": by_tier,
                "preexisting_conflicts": len(existing_conflicts.get("conflicts") or []),
            },
        },
    )

    manifest = read_jsonl(manifest_path)
    imported = 0
    for rec in manifest:
        fact_key = str(rec.get("fact_key") or "").strip()
        if not fact_key:
            continue
        if fact_key in existing_keys and resume:
            continue
        body = _fact_body_from_manifest(rec)
        mcp.call_tool(
            "memory_upsert_fact_v1",
            {
                "project_id": project_id,
                "kind": str(rec.get("kind") or "decision"),
                "key": fact_key,
                "body": body[:4000],
                "tier": 1,
                "source_type": "human",
                "actor": TAL_PHASE1_AGENT,
                "agent_id": TAL_PHASE1_AGENT,
                "skip_conflict_check": True,
                "skip_embedding": False,
            },
        )
        append_jsonl(
            exec_log,
            {
                "timestamp": iso_now(),
                "phase": 1,
                "agent_id": TAL_PHASE1_AGENT,
                "action": "fact_imported",
                "project": project_id,
                "result": {
                    "fact_key": fact_key,
                    "source_path": rec.get("source_path"),
                    "source_url": rec.get("source_url"),
                    "source_commit": rec.get("source_commit"),
                    "provenance_level": rec.get("provenance_level"),
                },
            },
        )
        imported += 1

    facts_after = list_all_facts(mcp, project_id)
    append_jsonl(
        exec_log,
        {
            "timestamp": iso_now(),
            "phase": 1,
            "agent_id": TAL_PHASE1_AGENT,
            "action": "graph_verified",
            "project": project_id,
            "result": {
                "node_count": len(facts_after),
                "imported_this_run": imported,
                "manifest_rows": len(manifest),
            },
        },
    )

    append_jsonl(
        checkpoints,
        {
            "timestamp": iso_now(),
            "phase": 1,
            "checkpoint_type": "phase_complete",
            "agent_id": TAL_PHASE1_AGENT,
            "project_id": project_id,
            "status": "complete",
            "metrics": {
                "total_facts": len(facts_after),
                "imported_this_run": imported,
                "manifest_rows": len(manifest),
                "ready_for_phase2": len(facts_after) >= len(manifest),
            },
        },
    )

    _write_phase1_report(
        project_id=project_id,
        total_facts=len(facts_after),
        imported=imported,
        manifest_rows=len(manifest),
    )
    print(
        f"TAL Phase 1 done. Imported {imported}/{len(manifest)} ADR facts into "
        f"{project_id}.  Log: {exec_log}",
        flush=True,
    )
    return 0


def _write_phase1_report(
    *, project_id: str, total_facts: int, imported: int, manifest_rows: int
) -> None:
    lines = [
        "# Phase 1 Report — Trusted ADR Lab",
        f"Generated: {iso_now()}",
        "",
        f"## Project: `{project_id}`",
        "",
        "### Corpus",
        f"- Manifest: `trusted-adr-lab/research/trusted_adr/adr_extracted_fact_manifest.jsonl`",
        f"- Source corpus: `joelparkerhenderson/architecture-decision-record` "
        "(≈4.6k GitHub stars, commit-pinned)",
        f"- ADR sections imported this run: **{imported}/{manifest_rows}**",
        f"- Total facts in TAL project after import: **{total_facts}**",
        "",
        "### Notes",
        "- TAL is intentionally edge-free: ADR files are self-contained "
        "decisions, so no `depends_on` / `implements` edges are created.",
        "- `dependency_impact` coverage is therefore marked **n/a** for "
        "this corpus (domain-absent, not a detector failure).",
        "- All 66 facts are source-URL grounded with commit SHAs for "
        "reproducibility (see `trusted_source_links.md`).",
        "",
    ]
    tal_phase1_report().write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Phase 2 / 2b shared injection loop
# ---------------------------------------------------------------------------
def _expected_type_for_row(row: dict[str, Any]) -> str:
    """Map TAL row → RDL-compatible ``expected_conflict_type`` string."""
    label = str(row.get("expected_label") or "").strip()
    if label == "needs_review":
        return "ambiguous_case"
    return label or str(row.get("expected_class") or "").strip()


def _row_group(row: dict[str, Any]) -> str:
    return str(row.get("row_group") or "")


def _row_key(row: dict[str, Any]) -> str:
    return str((row.get("proposed_fact") or {}).get("key") or "")


def _row_body(row: dict[str, Any]) -> str:
    return str((row.get("proposed_fact") or {}).get("body") or "")


def _row_kind(row: dict[str, Any]) -> str:
    return str((row.get("proposed_fact") or {}).get("kind") or "decision")


def _based_on_facts(row: dict[str, Any]) -> list[str]:
    return []


def _expected_anchor_keys(row: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for src in row.get("based_on_sources") or []:
        if not isinstance(src, dict):
            continue
        sp = str(src.get("source_path") or "").strip()
        if not sp:
            continue
        stem = sp.split("/")[-2] if sp.endswith("/index.md") else sp.split("/")[-1].replace(".md", "")
        if not stem:
            continue
        out.append(f"trusted_adr.fact.{stem}.decision")
    return out


def _inject_row(
    *,
    mcp: McpSession,
    project_id: str,
    row: dict[str, Any],
    injection_number: int,
    agent_id: str,
    poll_max_s: float,
) -> dict[str, Any]:
    """Inject a single TAL row and return the log record (minus envelope)."""
    row_id = str(row.get("row_id") or "")
    proposed_key = _row_key(row)
    body = _row_body(row)
    kind = _row_kind(row)
    expected_type = _expected_type_for_row(row)
    expected_anchors = _expected_anchor_keys(row)

    preflight_raw: Any | None = None
    preflight_err: str | None = None
    try:
        preflight_raw = memory_check_conflicts_v1(
            mcp,
            project_id,
            kind=kind,
            key=proposed_key,
            body=body,
            valid_from=(row.get("proposed_fact") or {}).get("valid_from"),
            valid_until=(row.get("proposed_fact") or {}).get("valid_until"),
            related_facts=[],
            include_semantic_trace=True,
            expected_anchor_keys=expected_anchors,
            conflict_execution_profile="research",
        )
    except Exception as e:
        preflight_err = str(e)

    row_group = _row_group(row)
    semantic_row = row_group in {"trusted_conflict", "trusted_ambiguity"} and expected_type in {
        "semantic_contradiction",
        "ambiguous_case",
    }

    sem_preflight = build_semantic_preflight_block(
        conflict_class=expected_type,
        preflight_raw=preflight_raw,
        preflight_error=preflight_err,
        semantic_track=semantic_row,
    )
    structural_preflight = build_structural_preflight_block(
        preflight_raw=preflight_raw,
        preflight_error=preflight_err,
    )

    # Governance outcome extraction (Wave 4.3) — pull from preflight envelope.
    gov_outcome = None
    if isinstance(preflight_raw, dict):
        gov_outcome = _governance_outcome_from_result(preflight_raw)
    if not gov_outcome:
        gov_outcome = _governance_outcome_from_result(
            {"cascade_trace": (preflight_raw or {}).get("cascade_trace")}
            if isinstance(preflight_raw, dict)
            else {}
        )

    t_write_start = time.time()
    err_msg: str | None = None
    write_resp: Any = None
    try:
        write_resp = mcp.call_tool(
            "memory_upsert_fact_v1",
            {
                "project_id": project_id,
                "kind": kind,
                "key": proposed_key,
                "body": body,
                "tier": 1,
                "source_type": "human",
                "actor": agent_id,
                "agent_id": agent_id,
                "skip_conflict_check": False,
                "skip_embedding": False,
            },
        )
    except Exception as e:
        err_msg = str(e)
    t_write_end = time.time()

    det = parse_detection(write_resp) if write_resp is not None else {}
    inline_available = detection_inline_available(write_resp) if write_resp is not None else False
    conflicts_n = int(det.get("conflicts_detected") or 0)
    conflict_types = list(det.get("conflict_types") or [])

    hit, poll_elapsed_s = poll_for_conflict_notification(
        mcp,
        project_id,
        {proposed_key},
        (t_write_end - 2.0) if t_write_end else None,
        interval_s=0.5,
        max_wait_s=poll_max_s,
        proposed_key=proposed_key,
    )
    notif_created = hit is not None
    notif_id = hit.get("id") if hit else None
    notif_severity = hit.get("severity") if hit else None
    notif_created_at = hit.get("created_at") if hit else None
    notif_conflict_type = hit.get("conflict_type") if hit else None
    observed_ms = (
        observed_notification_latency_ms(notif_created_at, t_write_end)
        if t_write_end and notif_created_at
        else None
    )

    inline_detected = (conflicts_n > 0) if inline_available else False
    preflight_severity = notif_severity or (
        (conflict_types[0] if conflict_types else None) if inline_available else None
    )

    structural_classes = {"dependency_impact", "constraint_violation", "temporal_invalidation"}
    inline_structural_types = [cls for cls in conflict_types if cls in structural_classes]
    async_structural_match = notif_conflict_type in structural_classes
    async_semantic_match = notif_conflict_type == "semantic_contradiction"
    inline_semantic_match = "semantic_contradiction" in conflict_types if inline_available else False

    semantic_primary_detected = semantic_preflight_detected(sem_preflight)
    semantic_primary_source = "preflight" if semantic_primary_detected else (
        "async_fallback" if async_semantic_match else
        "inline_fallback" if inline_semantic_match else
        "preflight_error" if sem_preflight.get("error") else
        "preflight"
    )
    if not semantic_primary_detected and (async_semantic_match or inline_semantic_match):
        semantic_primary_detected = True
    semantic_terminal_reason = (
        None if semantic_primary_detected else semantic_terminal_stop_reason(sem_preflight)
    )

    structural_primary_detected, structural_primary_source, structural_terminal_reason = (
        structural_primary_detection_result(
            structural_preflight=structural_preflight,
            expected_conflict_type=expected_type if expected_type in structural_classes else None,
            async_exact_type_match=async_structural_match,
            inline_exact_type_match=bool(inline_structural_types),
        )
    )

    row_contract = merge_row_contract_fields(sem_preflight, structural_preflight)
    # Re-run governance extraction against the merged row_contract (covers
    # servers that surface the outcome only at the contract level).
    if not gov_outcome:
        gov_outcome = _governance_outcome_from_result(row_contract)

    observed_types: set[str] = set()
    if semantic_primary_detected:
        observed_types.add("semantic_contradiction")
    observed_types.update(structural_preflight.get("classes_detected") or [])
    observed_types.update(inline_structural_types)
    if async_structural_match and notif_conflict_type:
        observed_types.add(str(notif_conflict_type))

    primary_detector_source = (
        semantic_primary_source if semantic_primary_detected else structural_primary_source
    )
    preflight_first_detected = row_contract.get("final_conflict_type") is not None
    preflight_type, _, preflight_terminal = _preflight_primary_prediction(
        {**row_contract, "governance_outcome": gov_outcome}
    )
    preflight_async_disagreement = bool(
        preflight_type and notif_conflict_type and preflight_type != notif_conflict_type
    )
    async_stronger_than_preflight = bool(
        notif_conflict_type and preflight_type is None and not preflight_terminal
    )
    detector_coherence = (
        "disagreement"
        if preflight_async_disagreement
        else "async_recovery"
        if async_stronger_than_preflight
        else "aligned"
        if (not notif_conflict_type or notif_conflict_type == preflight_type)
        else "preflight_only"
    )

    result_block: dict[str, Any] = {
        "fact_keys": [proposed_key],
        "expected_conflict_type": expected_type,
        "row_group": row_group,
        **row_contract,
        "governance_outcome": gov_outcome,
        "preflight_semantic": sem_preflight,
        "structural_preflight": structural_preflight,
        "preflight_has_semantic_conflicts": bool(sem_preflight.get("preflight_has_semantic_conflicts")),
        "preflight_has_structural_conflicts": bool(structural_preflight.get("preflight_has_structural_conflicts")),
        "semantic_trace_present": bool(sem_preflight.get("semantic_trace_present")),
        "semantic_trace_missing": bool(sem_preflight.get("semantic_trace_missing")),
        "semantic_trace": sem_preflight.get("semantic_trace"),
        "semantic_primary_detected": semantic_primary_detected,
        "semantic_primary_source": semantic_primary_source,
        "semantic_terminal_stop_reason": semantic_terminal_reason,
        "structural_primary_detected": structural_primary_detected,
        "structural_primary_source": structural_primary_source,
        "structural_terminal_stop_reason": structural_terminal_reason,
        "primary_detector_source": primary_detector_source,
        "preflight_first_detected": preflight_first_detected,
        "preflight_async_disagreement": preflight_async_disagreement,
        "async_stronger_than_preflight": async_stronger_than_preflight,
        "detector_coherence": detector_coherence,
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
            "matched_conflict_type": notif_conflict_type,
        },
        "notification": {
            "created": notif_created,
            "notification_id": notif_id,
            "conflict_type": notif_conflict_type,
            "severity": notif_severity,
            "created_at": notif_created_at,
        },
        "detection_latency_ms": det.get("detection_latency_ms"),
        "observed_conflict_types": sorted(observed_types),
        "success": err_msg is None,
    }
    if err_msg:
        result_block["error"] = err_msg

    record = {
        "timestamp": iso_now(),
        "phase": 2,
        "agent_id": agent_id,
        "action": "conflict_injected",
        "project": project_id,
        "injection_number": injection_number,
        "conflict_class": expected_type,
        "corpus_row_id": row_id,
        "based_on_facts": _based_on_facts(row),
        "proposed_fact_key": proposed_key,
        "result": result_block,
    }
    return record


def run_phase2(*, resume: bool = False) -> int:
    """Inject the 8 typed + 4 ambiguity TAL rows via preflight + upsert."""
    cfg = load_json(_spirl_cfg_path())
    project_id = load_tal_project_id(cfg)

    conflict_rows = read_jsonl(tal_conflict_rows())
    ambiguity_rows = read_jsonl(tal_ambiguity_rows())
    expected = tal_expected_counts()
    if len(conflict_rows) != expected["conflict"]:
        raise SystemExit(
            f"Expected {expected['conflict']} conflict rows, found {len(conflict_rows)} in "
            f"{tal_conflict_rows()}."
        )
    if len(ambiguity_rows) != expected["ambiguity"]:
        raise SystemExit(
            f"Expected {expected['ambiguity']} ambiguity rows, found {len(ambiguity_rows)} in "
            f"{tal_ambiguity_rows()}."
        )

    exec_log = tal_exec_log()
    checkpoints = tal_checkpoints()

    append_jsonl(
        checkpoints,
        {
            "timestamp": iso_now(),
            "phase": 2,
            "checkpoint_type": "phase_start" if not resume else "resume",
            "agent_id": TAL_AGENT_ID,
            "project_id": project_id,
            "status": "in_progress",
            "target_rows": len(conflict_rows) + len(ambiguity_rows),
        },
    )

    mcp = _open_mcp()
    all_rows = list(conflict_rows) + list(ambiguity_rows)
    poll_max_s = float(cfg.get("trusted_adr_lab_poll_max_s") or cfg.get("real_data_lab_poll_max_s") or 30.0)

    for idx, row in enumerate(all_rows):
        rec = _inject_row(
            mcp=mcp,
            project_id=project_id,
            row=row,
            injection_number=idx + 1,
            agent_id=TAL_AGENT_ID,
            poll_max_s=poll_max_s,
        )
        append_jsonl(exec_log, rec)
        print(
            f"[tal-phase2 {idx + 1}/{len(all_rows)}] {row.get('row_id')} "
            f"expected={rec['conflict_class']} gov={rec['result'].get('governance_outcome')}",
            flush=True,
        )

    append_jsonl(
        checkpoints,
        {
            "timestamp": iso_now(),
            "phase": 2,
            "checkpoint_type": "phase_complete",
            "agent_id": TAL_AGENT_ID,
            "project_id": project_id,
            "status": "complete",
            "total_injections": len(all_rows),
        },
    )
    _write_phase2_report(project_id=project_id, rows=all_rows)
    return 0


def _write_phase2_report(*, project_id: str, rows: list[dict[str, Any]]) -> None:
    by_group: dict[str, int] = {}
    for r in rows:
        by_group[_row_group(r)] = by_group.get(_row_group(r), 0) + 1
    lines = [
        "# Phase 2 Report — Trusted ADR Lab (typed + ambiguity injections)",
        f"Generated: {iso_now()}",
        "",
        f"## Project: `{project_id}`",
        "",
        "### Row distribution",
        "| row_group | count |",
        "|-----------|-------|",
    ]
    for g, n in sorted(by_group.items()):
        lines.append(f"| {g} | {n} |")
    lines.append("")
    lines.append("See `trusted_adr_lab_execution_log.jsonl` for the full "
                 "per-row preflight/governance envelope.")
    lines.append("")
    tal_phase2_report().write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_phase2b(*, resume: bool = False) -> int:
    """Inject the 6 benign TAL rows."""
    cfg = load_json(_spirl_cfg_path())
    project_id = load_tal_project_id(cfg)

    benign = read_jsonl(tal_benign_rows())
    expected = tal_expected_counts()
    if len(benign) != expected["benign"]:
        raise SystemExit(
            f"Expected {expected['benign']} benign rows, found {len(benign)} in "
            f"{tal_benign_rows()}."
        )

    exec_log = tal_exec_log()
    checkpoints = tal_checkpoints()
    append_jsonl(
        checkpoints,
        {
            "timestamp": iso_now(),
            "phase": 2,
            "checkpoint_type": "benign_phase_start",
            "agent_id": TAL_PHASE2B_AGENT,
            "project_id": project_id,
            "status": "in_progress",
            "target_rows": len(benign),
        },
    )

    mcp = _open_mcp()
    poll_max_s = float(cfg.get("trusted_adr_lab_poll_max_s") or cfg.get("real_data_lab_poll_max_s") or 30.0)
    for idx, row in enumerate(benign):
        rec = _inject_row(
            mcp=mcp,
            project_id=project_id,
            row=row,
            injection_number=idx + 1,
            agent_id=TAL_PHASE2B_AGENT,
            poll_max_s=poll_max_s,
        )
        # Force expected_conflict_type to "benign" in the log (the row's
        # ``expected_label`` is already "benign" but make sure the scorer's
        # resolver agrees).
        rec["conflict_class"] = "benign"
        rec["result"]["expected_conflict_type"] = "benign"
        append_jsonl(exec_log, rec)
        print(
            f"[tal-phase2b {idx + 1}/{len(benign)}] {row.get('row_id')} "
            f"gov={rec['result'].get('governance_outcome')}",
            flush=True,
        )

    append_jsonl(
        checkpoints,
        {
            "timestamp": iso_now(),
            "phase": 2,
            "checkpoint_type": "benign_phase_complete",
            "agent_id": TAL_PHASE2B_AGENT,
            "project_id": project_id,
            "status": "complete",
            "total_benign_injections": len(benign),
        },
    )
    return 0


# ---------------------------------------------------------------------------
# Phase 3 — TAL-specific scoring
# ---------------------------------------------------------------------------
_STRUCTURAL_CLASSES = {
    "dependency_impact",
    "constraint_violation",
    "temporal_invalidation",
}
_CORE4 = {"semantic_contradiction", *_STRUCTURAL_CLASSES}


def _tal_row_group_from_id(row_id: str) -> str:
    """Map TAL row_id prefixes to scoring buckets.

    ``d-sem-*``, ``d-con-*``, ``d-tmp-*`` → ``conflict``
    ``d-ben-*``                           → ``benign``
    ``d-amb-*``                           → ``ambiguous``
    """
    if row_id.startswith("d-ben-"):
        return "benign"
    if row_id.startswith("d-amb-"):
        return "ambiguous"
    if row_id.startswith("d-"):
        return "conflict"
    return "unknown"


def _derive_predicted_type_tal(
    res: dict[str, Any], expected: str
) -> tuple[str | None, str]:
    from real_data_lab_benign_mcp_run import _derive_predicted_type

    return _derive_predicted_type(res, expected)


def compute_tal_metrics(log_path: Path) -> dict[str, Any]:
    """TAL-flavored twin of ``compute_mixed_metrics_from_log``.

    Keys on TAL row_id prefixes instead of RDL's ``c-/b-/sb-`` and excludes
    ``dependency_impact`` from core-N recall (domain-absent in TAL).  The
    returned shape is a superset-compatible subset of the RDL metrics dict
    so the paper's main table can reuse the same columns.
    """
    if not log_path.exists():
        return {}
    tracked = ["semantic_contradiction", "constraint_violation", "temporal_invalidation"]
    by_class: dict[str, dict[str, int]] = {
        c: {"injected": 0, "binary_detected": 0, "exact_detected": 0,
            "cross_type_alerts": 0, "abstained": 0}
        for c in tracked
    }
    confusion: dict[str, dict[str, int]] = {}
    benign_fp_by_detector: dict[str, int] = {}

    conflict_total = 0
    core_n_total = 0
    core_n_exact = 0
    conflict_binary = 0
    conflict_exact = 0
    cross_type_alerts = 0
    abstain_total = 0

    benign_total = 0
    benign_fp = 0
    benign_tn = 0

    ambig_total = 0
    ambig_alerted = 0
    ambig_abstained = 0
    # "Forced typed" = ambiguous row that the detector committed to a typed
    # conflict class instead of routing to ``needs_review``.  This is the
    # quantity the Wave 4.3 Neyman-Pearson selector is designed to suppress.
    ambig_forced_typed = 0

    gov_counts: dict[str, int] = {"typed_conflict": 0, "needs_review": 0, "benign": 0, "unset": 0}
    ambig_needs_review = 0
    benign_needs_review = 0
    conflict_needs_review = 0

    for line in log_path.read_text(encoding="utf-8").splitlines():
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
        expected = str(res.get("expected_conflict_type") or o.get("conflict_class") or "")
        bucket = _tal_row_group_from_id(rid)

        predicted, _source = _derive_predicted_type_tal(res, expected)
        binary_alert = predicted is not None
        exact_match = expected in _CORE4 and predicted == expected
        cross_type = expected in _CORE4 and predicted is not None and predicted != expected
        abstained = predicted is None

        gov_outcome = _governance_outcome_from_result(res) or "unset"
        gov_counts[gov_outcome] = gov_counts.get(gov_outcome, 0) + 1
        is_needs_review = gov_outcome == _GOV_NEEDS_REVIEW

        if bucket == "conflict":
            conflict_total += 1
            if expected in by_class:
                by_class[expected]["injected"] += 1
                if binary_alert:
                    by_class[expected]["binary_detected"] += 1
                if exact_match:
                    by_class[expected]["exact_detected"] += 1
                if cross_type:
                    by_class[expected]["cross_type_alerts"] += 1
                if abstained:
                    by_class[expected]["abstained"] += 1
            if expected in _CORE4:
                core_n_total += 1
                if exact_match:
                    core_n_exact += 1
                if is_needs_review:
                    conflict_needs_review += 1
            if binary_alert:
                conflict_binary += 1
            if exact_match:
                conflict_exact += 1
            if cross_type:
                cross_type_alerts += 1
            if abstained:
                abstain_total += 1
            pred_key = predicted or "none"
            confusion.setdefault(expected or "unknown", {})
            confusion[expected or "unknown"][pred_key] = confusion[expected or "unknown"].get(pred_key, 0) + 1
        elif bucket == "benign":
            benign_total += 1
            if binary_alert:
                benign_fp += 1
                key = predicted or "unknown"
                benign_fp_by_detector[key] = benign_fp_by_detector.get(key, 0) + 1
            else:
                benign_tn += 1
            if is_needs_review:
                benign_needs_review += 1
        elif bucket == "ambiguous":
            ambig_total += 1
            if binary_alert:
                ambig_alerted += 1
            if abstained:
                ambig_abstained += 1
            if is_needs_review:
                ambig_needs_review += 1
            if binary_alert and not is_needs_review:
                ambig_forced_typed += 1

    tp = conflict_binary
    fn = conflict_total - conflict_binary
    fp = benign_fp
    tn = benign_tn
    pooled_precision = tp / (tp + fp) if (tp + fp) else 0.0
    pooled_recall = tp / (tp + fn) if (tp + fn) else 0.0
    core_n_exact_recall = (core_n_exact / core_n_total) if core_n_total else 0.0
    wrong_type_rate = (cross_type_alerts / conflict_total) if conflict_total else 0.0
    benign_spec = (benign_tn / benign_total) if benign_total else 0.0

    gov_tp = ambig_needs_review
    gov_fp = benign_needs_review
    gov_fn = conflict_needs_review
    needs_review_precision = gov_tp / (gov_tp + gov_fp) if (gov_tp + gov_fp) else 0.0
    needs_review_recall_ambig = ambig_needs_review / ambig_total if ambig_total else 0.0
    unsafe_forced_type_ambig = (
        ambig_forced_typed / ambig_total if ambig_total else 0.0
    )

    return {
        "corpus": "trusted_adr_lab",
        "conflict_total": conflict_total,
        "core_n_total": core_n_total,
        "core_n_exact_detected": core_n_exact,
        "core_n_exact_type_recall": core_n_exact_recall,
        "conflict_detected": conflict_binary,
        "conflict_recall": (conflict_binary / conflict_total) if conflict_total else 0.0,
        "conflict_detected_exact": conflict_exact,
        "conflict_exact_recall": (conflict_exact / conflict_total) if conflict_total else 0.0,
        "by_class": by_class,
        "confusion": confusion,
        "benign_total": benign_total,
        "benign_fp": benign_fp,
        "benign_tn": benign_tn,
        "benign_fp_rate": (benign_fp / benign_total) if benign_total else 0.0,
        "benign_fp_by_detector": dict(sorted(benign_fp_by_detector.items())),
        "benign_specificity": benign_spec,
        "ambiguous_rows_total": ambig_total,
        "ambiguous_alerted": ambig_alerted,
        "ambiguous_abstained": ambig_abstained,
        "ambiguous_forced_typed": ambig_forced_typed,
        "unsafe_forced_type_rate_ambiguous": unsafe_forced_type_ambig,
        "governance_outcome_counts": gov_counts,
        "ambiguous_needs_review": ambig_needs_review,
        "benign_needs_review": benign_needs_review,
        "conflict_needs_review": conflict_needs_review,
        "governance_needs_review_tp": gov_tp,
        "governance_needs_review_fp": gov_fp,
        "governance_needs_review_fn": gov_fn,
        "needs_review_precision": needs_review_precision,
        "needs_review_recall_ambiguous": needs_review_recall_ambig,
        "pooled_TP": tp,
        "pooled_FN": fn,
        "pooled_FP": fp,
        "pooled_TN": tn,
        "pooled_precision": pooled_precision,
        "pooled_recall": pooled_recall,
        "cross_type_alerts": cross_type_alerts,
        "wrong_type_alert_rate": wrong_type_rate,
        "abstain_total": abstain_total,
        "dependency_impact_coverage": "n/a",
        "dependency_impact_coverage_reason": (
            "ADR corpus has no dependency-edge substrate: plain-text ADRs "
            "cannot host `depends_on`/`implements` triples. Marked n/a "
            "rather than zero to avoid penalizing the detector for a "
            "domain-absent class (see Limitations)."
        ),
    }


def _pct(x: float | int) -> str:
    try:
        return f"{float(x) * 100:.1f}%"
    except (TypeError, ValueError):
        return str(x)


def run_phase3() -> int:
    cfg = load_json(_spirl_cfg_path())
    project_id = load_tal_project_id(cfg)
    exec_log = tal_exec_log()
    if not exec_log.exists():
        raise SystemExit(f"Missing TAL log: {exec_log} — run phases 1, 2, 2b first.")

    metrics = compute_tal_metrics(exec_log)
    tal_research_dir().mkdir(parents=True, exist_ok=True)

    _write_mixed_report(project_id, metrics)
    _write_confusion_matrix(metrics)
    _write_phase3_report(project_id, metrics)
    _write_paper3_experiment_d_report(metrics)

    append_jsonl(
        tal_checkpoints(),
        {
            "timestamp": iso_now(),
            "phase": 3,
            "checkpoint_type": "phase_complete",
            "agent_id": TAL_PHASE3_AGENT,
            "project_id": project_id,
            "status": "complete",
            "metrics_summary": {
                k: metrics.get(k)
                for k in (
                    "conflict_recall",
                    "core_n_exact_type_recall",
                    "benign_fp_rate",
                    "needs_review_precision",
                    "unsafe_forced_type_rate_ambiguous",
                )
            },
        },
    )
    print(
        f"TAL Phase 3 done. core-N exact-type recall={metrics.get('core_n_exact_type_recall')}, "
        f"benign FP rate={metrics.get('benign_fp_rate')}, "
        f"needs_review precision={metrics.get('needs_review_precision')}",
        flush=True,
    )
    return 0


def _write_mixed_report(project_id: str, m: dict[str, Any]) -> None:
    lines = [
        "# Trusted ADR Lab — Mixed Workload Report (Wave 4)",
        f"Generated: {iso_now()}",
        f"Project: `{project_id}`",
        "",
        "## Workload",
        f"- Typed conflict rows: **{m.get('conflict_total', 0)}** "
        f"(semantic={m['by_class'].get('semantic_contradiction', {}).get('injected', 0)}, "
        f"constraint={m['by_class'].get('constraint_violation', {}).get('injected', 0)}, "
        f"temporal={m['by_class'].get('temporal_invalidation', {}).get('injected', 0)})",
        f"- Ambiguity rows: **{m.get('ambiguous_rows_total', 0)}**",
        f"- Benign rows: **{m.get('benign_total', 0)}**",
        "",
        "## Pooled detection",
        f"- Binary recall (conflict rows only): **{_pct(m.get('conflict_recall', 0))}**",
        f"- Core-N exact-type recall "
        f"(semantic+constraint+temporal, `dependency_impact=n/a`): "
        f"**{_pct(m.get('core_n_exact_type_recall', 0))}**",
        f"- Pooled precision (typed TP / (TP + benign FP)): "
        f"**{_pct(m.get('pooled_precision', 0))}**",
        f"- Benign specificity: **{_pct(m.get('benign_specificity', 0))}** "
        f"(FP rate: {_pct(m.get('benign_fp_rate', 0))})",
        f"- Wrong-type alert rate on typed rows: "
        f"**{_pct(m.get('wrong_type_alert_rate', 0))}**",
        "",
        "## Per-class exact-type recall",
        "| class | injected | binary | exact | cross-type | abstained |",
        "|-------|---------:|-------:|------:|-----------:|----------:|",
    ]
    for c in ("semantic_contradiction", "constraint_violation", "temporal_invalidation"):
        st = m["by_class"].get(c, {})
        lines.append(
            f"| `{c}` | {st.get('injected', 0)} | {st.get('binary_detected', 0)} | "
            f"{st.get('exact_detected', 0)} | {st.get('cross_type_alerts', 0)} | "
            f"{st.get('abstained', 0)} |"
        )
    lines.append("| `dependency_impact` | n/a | n/a | n/a | n/a | n/a |")
    lines.append("")
    lines.append("> Footnote — `dependency_impact` is **domain-absent** in TAL: "
                 "ADRs are self-contained markdown files with no cross-document "
                 "`depends_on` / `implements` triples.  Marked `n/a` to avoid "
                 "penalizing the detector for a class the corpus cannot express.")
    lines.append("")

    gov = m.get("governance_outcome_counts", {})
    lines.extend([
        "## Governance outcome (Wave 4.3)",
        f"- `needs_review` precision "
        f"(ambig→needs_review / (ambig+benign→needs_review)): "
        f"**{_pct(m.get('needs_review_precision', 0))}**",
        f"- `needs_review` recall on ambiguous rows: "
        f"**{_pct(m.get('needs_review_recall_ambiguous', 0))}**",
        f"- Unsafe forced-type rate on ambiguous rows: "
        f"**{_pct(m.get('unsafe_forced_type_rate_ambiguous', 0))}**",
        f"- Outcome counts: "
        f"`typed_conflict`={gov.get('typed_conflict', 0)}, "
        f"`needs_review`={gov.get('needs_review', 0)}, "
        f"`benign`={gov.get('benign', 0)}, "
        f"`unset`={gov.get('unset', 0)}",
        "",
        "## Benign FP detector breakdown",
        "| detector | count |",
        "|----------|------:|",
    ])
    for d, n in m.get("benign_fp_by_detector", {}).items():
        lines.append(f"| `{d}` | {n} |")
    if not m.get("benign_fp_by_detector"):
        lines.append("| — | 0 |")
    lines.append("")
    lines.append(
        "## Notes\n\n"
        "- Metrics computed by `scripts/trusted_adr_lab_mcp_pipeline.py::compute_tal_metrics`.\n"
        "- Scoring contract matches RDL: same preflight/async resolver, same "
        "`governance_outcome` extraction, same row_contract shape.\n"
        "- References: Neyman-Pearson selector (arXiv:2505.15008), "
        "AbstentionBench protocol (arXiv:2506.09038)."
    )
    tal_mixed_report().write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_confusion_matrix(m: dict[str, Any]) -> None:
    classes = ["semantic_contradiction", "constraint_violation", "temporal_invalidation"]
    preds = [*classes, "none"]
    lines = [
        "# Trusted ADR Lab — Confusion Matrix",
        f"Generated: {iso_now()}",
        "",
        "Rows = expected class, columns = predicted class; `none` column "
        "captures abstentions (typed-conflict silence plus `needs_review` "
        "routing).",
        "",
        "| expected \\ predicted | " + " | ".join(f"`{p}`" for p in preds) + " |",
        "|---" * (len(preds) + 1) + "|",
    ]
    for c in classes:
        row = [f"`{c}`"] + [str((m.get("confusion", {}).get(c) or {}).get(p, 0)) for p in preds]
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")
    tal_confusion_matrix().write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_phase3_report(project_id: str, m: dict[str, Any]) -> None:
    lines = [
        "# Phase 3 Report — Trusted ADR Lab (Wave 4 scoring)",
        f"Generated: {iso_now()}",
        f"Project: `{project_id}`",
        "",
        f"- Core-N exact-type recall: **{_pct(m.get('core_n_exact_type_recall', 0))}**",
        f"- Binary conflict recall: **{_pct(m.get('conflict_recall', 0))}**",
        f"- Benign FP rate: **{_pct(m.get('benign_fp_rate', 0))}**",
        f"- `needs_review` precision: **{_pct(m.get('needs_review_precision', 0))}**",
        f"- Unsafe forced-type rate on ambiguous rows: "
        f"**{_pct(m.get('unsafe_forced_type_rate_ambiguous', 0))}**",
        "",
        "See `trusted_adr_lab_mixed_report.md` for the full breakdown and "
        "`trusted_adr_lab_confusion_matrix.md` for the per-class confusion "
        "matrix.",
        "",
    ]
    tal_phase3_report().write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_paper3_experiment_d_report(m: dict[str, Any]) -> None:
    """Companion report written to the legacy paper3 D-experiment path so
    the EMNLP appendix can reference it without repathing."""
    out = tal_research_dir() / "paper3_phase3_report.experiment_D.md"
    lines = [
        "# paper3 Experiment D — Trusted ADR Lab (Wave 4)",
        f"Generated: {iso_now()}",
        "",
        "This companion report re-reports the Wave 4 TAL metrics against the ",
        "legacy `experiment_D` identifier used by earlier paper drafts.",
        "",
        "| metric | value |",
        "|--------|------:|",
        f"| Core-N exact-type recall | **{_pct(m.get('core_n_exact_type_recall', 0))}** |",
        f"| Conflict binary recall | {_pct(m.get('conflict_recall', 0))} |",
        f"| Benign FP rate | {_pct(m.get('benign_fp_rate', 0))} |",
        f"| `needs_review` precision | {_pct(m.get('needs_review_precision', 0))} |",
        f"| `needs_review` recall (ambiguous) | "
        f"{_pct(m.get('needs_review_recall_ambiguous', 0))} |",
        f"| Unsafe forced-type rate (ambiguous) | "
        f"{_pct(m.get('unsafe_forced_type_rate_ambiguous', 0))} |",
        f"| `dependency_impact` coverage | n/a (domain-absent) |",
        "",
        "> `dependency_impact` is **n/a** rather than zero because TAL's "
        "plain-text ADR corpus has no cross-document dependency triples.  "
        "This is an honest corpus-scope limitation, not a detector failure.",
        "",
    ]
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")


__all__ = [
    "run_phase1",
    "run_phase2",
    "run_phase2b",
    "run_phase3",
    "compute_tal_metrics",
    "load_tal_project_id",
]
