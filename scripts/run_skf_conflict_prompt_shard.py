#!/usr/bin/env python3
"""
Execute a shard of conflict prompts from JSONL (deterministic upserts + edges).

Uses the same MCP JSON-RPC session as ``adr_corpus_mcp_pipeline.py``.
Sharding lets you run 4 terminals or 4 sub-agents in parallel:

  python run_skf_conflict_prompt_shard.py --jsonl ../research/conflict_prompts.live.jsonl \\
      --shard-index 0 --shard-count 4 --project-id <UUID>

Options:
  --dry-run   Print actions only
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from adr_corpus_mcp_pipeline import load_json, mcp_from_config, save_last_response, spirl_config_path  # noqa: E402


def shard_slice(lines: list[str], index: int, count: int) -> list[str]:
    return [ln for i, ln in enumerate(lines) if i % count == index]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jsonl", type=Path, required=True)
    ap.add_argument("--shard-index", type=int, default=0)
    ap.add_argument("--shard-count", type=int, default=1)
    ap.add_argument("--project-id", type=str, default="")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    cfg = load_json(spirl_config_path())
    project_id = args.project_id.strip()
    if not project_id:
        project_id = (cfg.get("adr_reference_project_id") or "").strip()
    if not project_id:
        project_id = str((cfg.get("projects") or {}).get("paper3_adr_reference") or "").strip()
    if not project_id:
        project_id = str(cfg.get("project_id") or "").strip()
    if not project_id:
        raise SystemExit("Set --project-id or populate .spirl/config.json (adr_reference_project_id or project_id)")

    raw_lines = [ln for ln in args.jsonl.read_text(encoding="utf-8").splitlines() if ln.strip()]
    lines = shard_slice(raw_lines, args.shard_index, args.shard_count)
    print(f"Shard {args.shard_index}/{args.shard_count}: {len(lines)} prompts")

    if args.dry_run:
        for ln in lines:
            print(ln[:200] + ("…" if len(ln) > 200 else ""))
        return

    mcp, _ = mcp_from_config()
    mcp.connect()

    for ln in lines:
        row = json.loads(ln)
        tool = row.get("mcp_tool")
        pid = project_id
        if tool == "memory_upsert_fact_v1":
            spec = row.get("deterministic_upsert")
            if not spec:
                print("skip (no deterministic_upsert):", row.get("prompt_id"))
                continue
            payload = {"project_id": pid, "product_id": "spirl", **spec}
            res = mcp.call_tool("memory_upsert_fact_v1", payload)
            save_last_response(res)
            print(row.get("prompt_id"), "->", res.get("status", res) if isinstance(res, dict) else "ok")
        elif tool == "create_fact_edge":
            es = row.get("edge_spec") or {}
            res = mcp.call_tool(
                "create_fact_edge",
                {
                    "project_id": pid,
                    "source_fact_key": es.get("source_fact_key"),
                    "target_fact_key": es.get("target_fact_key"),
                    "edge_type": es.get("edge_type", "depends_on"),
                    "metadata": {"prompt_id": row.get("prompt_id"), "shard": args.shard_index},
                },
            )
            save_last_response(res)
            print(row.get("prompt_id"), "edge ->", res)
        else:
            print("skip unknown tool", tool, row.get("prompt_id"))


if __name__ == "__main__":
    main()
