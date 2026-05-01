#!/usr/bin/env python3
"""
Real Data Lab Phase 1 — corpus verification and edge creation via Spirl MCP (Streamable HTTP JSON-RPC).

Same MCP transport as scripts/paper3_phase1_mcp_run.py and Cursor (.cursor/mcp.json), not raw REST paths.
Reads edge plan from real-data-lab/research/rdl_phase1_edges_plan.json (built from corpus keys).
"""
from __future__ import annotations

import argparse
import json
import sys
from argparse import Namespace
from collections import defaultdict
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from paper3_paths import btc_root, mcp_json_path, spirl_config_path
from rdl_pipeline_execution_lock import rdl_pipeline_lock
from paper3_phase1_mcp_run import (
    McpSession,
    aggregate_facts,
    append_jsonl,
    degree_by_key,
    edge_key_set,
    iso_now,
    list_all_edges,
    list_all_facts,
    load_json,
)

RDL = btc_root() / "real-data-lab"
RESEARCH = RDL / "research"
CHECKPOINTS = RESEARCH / "real_data_lab_checkpoints.jsonl"
EXEC_LOG = RESEARCH / "real_data_lab_execution_log.jsonl"
PAUSE_FLAG = RESEARCH / "real_data_lab_pause.flag"
EDGES_PLAN = RESEARCH / "rdl_phase1_edges_plan.json"
REPORT_PATH = RESEARCH / "real_data_lab_phase1_report.md"
CONFIG_PATH = spirl_config_path()
MCP_PATH = mcp_json_path()

AGENT = "rdl_phase1_corpus_builder"
SLUG = "project_core_platform"


def log_has_baseline_for_project(path: Path, project_id: str) -> bool:
    if not path.exists() or path.stat().st_size == 0:
        return False
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            o = json.loads(line)
        except json.JSONDecodeError:
            continue
        if (
            o.get("phase") == 1
            and o.get("action") == "baseline_snapshot"
            and o.get("project") == project_id
        ):
            return True
    return False


def archive_if_nonempty(path: Path, label: str) -> None:
    if not path.exists() or path.stat().st_size == 0:
        return
    adir = RESEARCH / "archive"
    adir.mkdir(parents=True, exist_ok=True)
    ts = iso_now().replace(":", "").replace("T", "_")
    dest = adir / f"{path.stem}_{label}_{ts}{path.suffix}"
    dest.write_bytes(path.read_bytes())


def load_project_id(cfg: dict) -> str:
    pid = cfg.get("real_data_lab_project_id")
    if pid:
        return str(pid)
    p = cfg.get("projects") or {}
    v = p.get("real_data_lab_project_core_platform")
    if v:
        return str(v)
    raise SystemExit("Set real_data_lab_project_id in .spirl/config.json")


def write_report(project_id: str, lines_read: int) -> None:
    entries: list[dict] = []
    for line in EXEC_LOG.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            o = json.loads(line)
        except json.JSONDecodeError:
            continue
        if o.get("phase") == 1:
            entries.append(o)

    snap = next((e for e in entries if e.get("action") == "baseline_snapshot"), None)
    ver = None
    for e in entries:
        if e.get("action") == "graph_verified":
            ver = e
    resolved = [e for e in entries if e.get("action") == "conflict_resolved"]
    edges_n = sum(1 for e in entries if e.get("action") == "edge_created")

    by_kind = (snap or {}).get("result", {}).get("by_kind") or {}
    total = (snap or {}).get("result", {}).get("total_facts", 0)
    pre_c = (snap or {}).get("result", {}).get("preexisting_conflicts", 0)

    lines = [
        "# Phase 1 Report — Real Data Lab (single corpus)",
        f"Generated: {iso_now()}",
        "",
        f"## Project: Project Core Platform (`{project_id}`)",
        "",
        "### Baseline snapshot",
        "",
        "| kind | count |",
        "|------|-------|",
    ]
    for k, v in sorted(by_kind.items()):
        lines.append(f"| {k} | {v} |")
    lines.append(f"| **TOTAL** | **{total}** |")
    lines.append("")
    lines.append(f"Pre-existing conflicts found: {pre_c}")
    lines.append(f"Pre-existing conflicts resolved: {len(resolved)}")
    lines.append("Clean baseline after cleanup: yes" if pre_c == len(resolved) else "Clean baseline after cleanup: partial")
    lines.append("")
    lines.append("### Edge creation")
    lines.append(f"Edges created (logged): {edges_n}")
    lines.append("")
    lines.append("### Graph verification")
    if ver:
        r = ver.get("result") or {}
        lines.append(f"- Node count: {r.get('node_count')}")
        lines.append(f"- Edge count: {r.get('edge_count')}")
        lines.append(f"- Isolated nodes (all kinds): {r.get('isolated_nodes')}")
        if r.get("isolated_skf_nodes") is not None:
            lines.append(f"- Isolated SKF corpus facts (`f-*` keys): {r.get('isolated_skf_nodes')}")
        if r.get("corpus_skf_nodes_in_edge_plan") is not None:
            lines.append(f"- SKF keys covered by edge plan: {r.get('corpus_skf_nodes_in_edge_plan')}")
        lines.append(f"- Connected (all nodes): {r.get('connected')}")
        if r.get("skf_subgraph_connected") is not None:
            lines.append(f"- SKF subgraph connected (no isolated `f-*`): {r.get('skf_subgraph_connected')}")
        ebt = r.get("edges_by_type") or {}
        if ebt:
            lines.append("- Edges by type:")
            for t, n in sorted(ebt.items()):
                lines.append(f"  - `{t}`: {n}")
    else:
        lines.append("_No graph_verified log entry._")
    lines.append("")
    lines.append("### Overall status")
    lines.append(f"- Phase 1 log lines (phase==1): {len(entries)}")
    lines.append(f"- Report source lines scanned: {lines_read}")
    if ver:
        r = ver.get("result") or {}
        if r.get("isolated_skf_nodes") == 0 and (r.get("isolated_nodes") or 0) > 0:
            lines.append(
                "- Imported SKF facts (`f-*`) all have ≥1 graph edge; remaining isolated nodes are "
                "`research` summary upserts only."
            )
    lines.append("")
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description="RDL Phase 1 via Spirl MCP.")
    ap.add_argument(
        "--resume",
        action="store_true",
        help="Keep existing execution log and checkpoints; skip baseline snapshot/upsert if already logged for this project.",
    )
    ap.add_argument(
        "--ignore-pipeline-lock",
        action="store_true",
        help="Skip real_data_lab_pipeline.lock (only if no other RDL script is writing the execution log).",
    )
    args = ap.parse_args()

    with rdl_pipeline_lock(ignore=bool(args.ignore_pipeline_lock)):
        phase1_run(args)


def phase1_run(args: Namespace) -> None:
    RESEARCH.mkdir(parents=True, exist_ok=True)
    if not EDGES_PLAN.exists():
        raise SystemExit(f"Missing edge plan: {EDGES_PLAN} — run scripts/build_rdl_phase1_edges.py first.")

    cfg = load_json(CONFIG_PATH)
    project_id = load_project_id(cfg)
    mcp_url = cfg.get("api_base", "http://localhost:8000").rstrip("/") + "/mcp"
    mcp_cfg = load_json(MCP_PATH)
    token = mcp_cfg["mcpServers"]["spirl"]["headers"]["Authorization"]

    if not args.resume:
        archive_if_nonempty(EXEC_LOG, "pre_redo")
        archive_if_nonempty(CHECKPOINTS, "pre_redo")
        EXEC_LOG.write_text("", encoding="utf-8")
        CHECKPOINTS.write_text("", encoding="utf-8")

        append_jsonl(
            CHECKPOINTS,
            {
                "timestamp": iso_now(),
                "phase": 1,
                "checkpoint_type": "phase_start",
                "agent_id": AGENT,
                "status": "in_progress",
                "prerequisites_checked": True,
                "notes": "Real Data Lab Phase 1 — corpus verification (fresh run)",
            },
        )
    else:
        append_jsonl(
            CHECKPOINTS,
            {
                "timestamp": iso_now(),
                "phase": 1,
                "checkpoint_type": "resume",
                "agent_id": AGENT,
                "status": "in_progress",
                "project": project_id,
                "notes": "Resuming Phase 1 — logs preserved",
            },
        )

    mcp = McpSession(mcp_url, token)
    mcp.connect()

    mcp.call_tool("get_pm_context", {"project_id": project_id})
    facts = list_all_facts(mcp, project_id)
    by_kind, by_tier = aggregate_facts(facts)

    conflicts = mcp.call_tool(
        "list_conflicts_v1", {"project_id": project_id, "limit": 200, "unresolved_only": True}
    )
    if isinstance(conflicts, str):
        try:
            conflicts = json.loads(conflicts)
        except json.JSONDecodeError:
            conflicts = {}
    if not isinstance(conflicts, dict):
        conflicts = {}
    conflict_list = conflicts.get("conflicts") or []
    pre_n = len(conflict_list)

    for c in conflict_list:
        cid = c.get("id") or c.get("conflict_id")
        if not cid:
            continue
        mcp.call_tool(
            "resolve_conflict_v1",
            {
                "project_id": project_id,
                "conflict_id": str(cid),
                "resolution": "accepted",
                "resolved_by": AGENT,
            },
        )
        append_jsonl(
            EXEC_LOG,
            {
                "timestamp": iso_now(),
                "phase": 1,
                "agent_id": AGENT,
                "action": "conflict_resolved",
                "project": project_id,
                "result": {
                    "conflict_id": str(cid),
                    "resolution": "accepted",
                    "resolution_notes": "resolved before research baseline — pre-existing noise",
                },
            },
        )

    skip_baseline = args.resume and log_has_baseline_for_project(EXEC_LOG, project_id)
    baseline_key = f"research.rdl.baseline.{SLUG}"
    existing_keys = {str(f.get("key")) for f in facts if f.get("key")}
    baseline_body = (
        f"Baseline snapshot: {len(facts)} facts; kinds: {by_kind}; "
        f"pre-existing conflicts resolved: {pre_n}."
    )
    if not skip_baseline:
        append_jsonl(
            EXEC_LOG,
            {
                "timestamp": iso_now(),
                "phase": 1,
                "agent_id": AGENT,
                "action": "baseline_snapshot",
                "project": project_id,
                "result": {
                    "total_facts": len(facts),
                    "by_kind": by_kind,
                    "by_tier": by_tier,
                    "preexisting_conflicts": pre_n,
                },
            },
        )

        mcp.call_tool(
            "memory_upsert_fact_v1",
            {
                "project_id": project_id,
                "kind": "research",
                "key": baseline_key,
                "body": baseline_body,
                "tier": 1,
                "source_type": "human",
                "actor": AGENT,
                "skip_embedding": True,
                "skip_conflict_check": True,
            },
        )
    elif baseline_key not in existing_keys:
        # Resume after a crash that logged baseline_snapshot but did not finish the upsert.
        mcp.call_tool(
            "memory_upsert_fact_v1",
            {
                "project_id": project_id,
                "kind": "research",
                "key": baseline_key,
                "body": baseline_body,
                "tier": 1,
                "source_type": "human",
                "actor": AGENT,
                "skip_embedding": True,
                "skip_conflict_check": True,
            },
        )

    plan = load_json(EDGES_PLAN)
    if isinstance(plan, list):
        edge_rows = [
            {
                "from": r["source"],
                "to": r["target"],
                "edge_type": r["edge_type"],
                "justification": r.get("justification") or "",
            }
            for r in plan
        ]
    else:
        edge_rows = plan.get("edges") or []
    log_n = (0 if skip_baseline else 2) + len(conflict_list)

    facts_pre_edges = list_all_facts(mcp, project_id)
    edges_pre = list_all_edges(mcp, project_id)
    id_to_key_pre = {
        str(f["id"]): str(f["key"]) for f in facts_pre_edges if f.get("id") and f.get("key")
    }
    existing_triples = edge_key_set(edges_pre, id_to_key_pre)

    for row in edge_rows:
        if PAUSE_FLAG.is_file():
            append_jsonl(
                CHECKPOINTS,
                {
                    "timestamp": iso_now(),
                    "phase": 1,
                    "checkpoint_type": "operator_pause",
                    "agent_id": AGENT,
                    "status": "paused",
                    "project": project_id,
                    "notes": "Remove real-data-lab/research/real_data_lab_pause.flag and re-run Phase 1 to continue.",
                },
            )
            print(
                "PAUSED: remove real-data-lab/research/real_data_lab_pause.flag then re-run Phase 1.",
                flush=True,
            )
            return
        src = row["from"]
        tgt = row["to"]
        et = row["edge_type"]
        jus = row.get("justification") or ""
        if (src, tgt, et) in existing_triples:
            continue
        try:
            mcp.call_tool(
                "create_fact_edge",
                {
                    "project_id": project_id,
                    "source_fact_key": src,
                    "target_fact_key": tgt,
                    "edge_type": et,
                },
            )
        except Exception as exc:
            append_jsonl(
                EXEC_LOG,
                {
                    "timestamp": iso_now(),
                    "phase": 1,
                    "agent_id": AGENT,
                    "action": "edge_create_failed",
                    "project": project_id,
                    "result": {"from_key": src, "to_key": tgt, "edge_type": et, "error": str(exc)},
                },
            )
            log_n += 1
            continue
        existing_triples.add((src, tgt, et))
        existing_triples.add((tgt, src, et))
        append_jsonl(
            EXEC_LOG,
            {
                "timestamp": iso_now(),
                "phase": 1,
                "agent_id": AGENT,
                "action": "edge_created",
                "project": project_id,
                "result": {
                    "from_key": src,
                    "edge_type": et,
                    "to_key": tgt,
                    "justification": jus,
                },
            },
        )
        log_n += 1

    parts: list[str] = []
    for row in edge_rows:
        parts.append(f"{row['from']} --{row['edge_type']}--> {row['to']}: {row.get('justification', '')}")
    summary_body = " | ".join(parts)[:12000]
    mcp.call_tool(
        "memory_upsert_fact_v1",
        {
            "project_id": project_id,
            "kind": "research",
            "key": f"research.rdl.edges.justification.{SLUG}",
            "body": summary_body,
            "tier": 1,
            "source_type": "human",
            "actor": AGENT,
            "skip_embedding": True,
            "skip_conflict_check": True,
        },
    )

    facts_final = list_all_facts(mcp, project_id)
    edges_after = list_all_edges(mcp, project_id)
    id_to_key = {str(f["id"]): str(f["key"]) for f in facts_final if f.get("id") and f.get("key")}
    deg = degree_by_key(edges_after, id_to_key)
    # id_to_key maps fact UUID -> fact key; isolate using human-readable keys, not UUID dict keys
    isolated = sorted(v for v in id_to_key.values() if deg.get(v, 0) == 0)
    edges_by_type: dict[str, int] = defaultdict(int)
    for e in edges_after:
        edges_by_type[str(e.get("edge_type") or "?")] += 1

    skf_isolated = [k for k in isolated if not str(k).startswith("research.")]
    skf_keys_in_plan: set[str] = set()
    for row in edge_rows:
        skf_keys_in_plan.add(row["from"])
        skf_keys_in_plan.add(row["to"])

    append_jsonl(
        EXEC_LOG,
        {
            "timestamp": iso_now(),
            "phase": 1,
            "agent_id": AGENT,
            "action": "graph_verified",
            "project": project_id,
            "result": {
                "node_count": len(facts_final),
                "edge_count": len(edges_after),
                "edges_by_type": dict(edges_by_type),
                "isolated_nodes": len(isolated),
                "isolated_node_keys": isolated,
                "isolated_skf_nodes": len(skf_isolated),
                "isolated_skf_node_keys": skf_isolated,
                "corpus_skf_nodes_in_edge_plan": len(skf_keys_in_plan),
                "connected": len(isolated) == 0,
                "skf_subgraph_connected": len(skf_isolated) == 0,
            },
        },
    )
    log_n += 1

    append_jsonl(
        CHECKPOINTS,
        {
            "timestamp": iso_now(),
            "phase": 1,
            "checkpoint_type": "project_complete",
            "agent_id": AGENT,
            "project": project_id,
            "status": "complete",
            "metrics": {
                "total_facts": len(facts_final),
                "total_edges": len(edges_after),
                "isolated_nodes": len(isolated),
                "isolated_skf_nodes": len(skf_isolated),
                "skf_corpus_nodes_in_edge_plan": len(skf_keys_in_plan),
                "ready_for_phase2": len(skf_isolated) == 0 and len(edges_after) > 0,
            },
        },
    )

    phase1_lines = 0
    for line in EXEC_LOG.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            o = json.loads(line)
        except json.JSONDecodeError:
            continue
        if o.get("phase") == 1:
            phase1_lines += 1
    write_report(project_id, phase1_lines)
    append_jsonl(
        CHECKPOINTS,
        {
            "timestamp": iso_now(),
            "phase": 1,
            "checkpoint_type": "phase_complete",
            "agent_id": AGENT,
            "status": "complete",
            "report_generated": True,
            "report_path": "real-data-lab/research/real_data_lab_phase1_report.md",
            "log_entries_written": phase1_lines,
            "next_phase_prerequisites_met": len(skf_isolated) == 0,
            "notes": "Real Data Lab Phase 1 complete for single corpus project",
        },
    )
    print("Done. Log:", EXEC_LOG, "Report:", REPORT_PATH, "edges:", len(edges_after))
    print(
        "Next (same project, Beyond Temporal Contradiction/scripts): "
        "python real_data_lab_phase2_mcp_run.py -> python real_data_lab_benign_mcp_run.py -> "
        "python real_data_lab_phase3_mcp_run.py",
        flush=True,
    )


if __name__ == "__main__":
    main()
