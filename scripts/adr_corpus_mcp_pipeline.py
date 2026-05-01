#!/usr/bin/env python3
"""
ADR real-corpus track — Spirl MCP quick_start + onboard + read-only phases 1–4.

Uses the cloned repo at ``external/architecture-decision-record/`` (CONTEXT.md + README + EN examples).

Writes experiment-specific artifacts (does not touch synthetic Experiment C logs):
  research/paper3_checkpoints.experiment_ADR.jsonl
  research/paper3_execution_log.experiment_ADR.jsonl
  research/paper3_adr_phase{1,2,3,4}_report.md
  research/adr_mcp_last_response.json  (debug: last tool return)

Updates repo-root ``.spirl/config.json`` with:
  adr_reference_project_id
  projects.paper3_adr_reference
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from paper3_paths import btc_root, mcp_json_path, research_dir, spirl_config_path

try:
    import requests
except ImportError as e:  # pragma: no cover
    raise SystemExit("pip install requests") from e

MAX_CHARS_PER_FILE = 100_000
UUID_RE = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.I
)


def iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def append_jsonl(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save_last_response(obj: Any) -> None:
    p = research_dir() / "adr_mcp_last_response.json"
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def find_uuid_in_obj(obj: Any) -> str | None:
    """Best-effort project UUID from nested dict/list/string."""
    if obj is None:
        return None
    if isinstance(obj, str):
        m = UUID_RE.search(obj)
        return m.group(0) if m else None
    if isinstance(obj, dict):
        for k in ("project_id", "id", "projectId", "uuid"):
            v = obj.get(k)
            if isinstance(v, str) and UUID_RE.fullmatch(v.strip()):
                return v.strip()
        for v in obj.values():
            u = find_uuid_in_obj(v)
            if u:
                return u
    if isinstance(obj, list):
        for it in obj:
            u = find_uuid_in_obj(it)
            if u:
                return u
    return None


class McpSession:
    def __init__(self, url: str, token: str) -> None:
        self.url = url.rstrip("/")
        self.headers = {
            "Authorization": token,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        self.session_id: str | None = None
        self._next_id = 1

    def _rpc(self, method: str, params: dict | None = None) -> dict:
        mid = self._next_id
        self._next_id += 1
        payload = {"jsonrpc": "2.0", "id": mid, "method": method, "params": params or {}}
        hdrs = dict(self.headers)
        if self.session_id:
            hdrs["Mcp-Session-Id"] = self.session_id
        r = requests.post(self.url, headers=hdrs, json=payload, timeout=600)
        r.raise_for_status()
        body = r.json()
        if "error" in body and body["error"]:
            raise RuntimeError(f"MCP {method}: {body['error']}")
        return body.get("result", body)

    def connect(self) -> None:
        r = requests.post(
            self.url,
            headers=self.headers,
            json={
                "jsonrpc": "2.0",
                "id": self._next_id,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "adr_corpus_mcp_pipeline", "version": "1.0"},
                },
            },
            timeout=120,
        )
        r.raise_for_status()
        sid = r.headers.get("mcp-session-id") or r.headers.get("Mcp-Session-Id")
        if not sid:
            raise RuntimeError("No mcp-session-id header from initialize")
        self.session_id = sid
        self._next_id += 1

    def call_tool(self, name: str, arguments: dict) -> Any:
        last: Exception | None = None
        for attempt, delay in enumerate([1.0, 2.0, 4.0]):
            try:
                res = self._rpc("tools/call", {"name": name, "arguments": arguments})
                if not res or "content" not in res:
                    return res
                parts = res.get("content") or []
                for p in parts:
                    if isinstance(p, dict) and p.get("type") == "text":
                        txt = p.get("text") or ""
                        try:
                            return json.loads(txt)
                        except json.JSONDecodeError:
                            return txt
                return res
            except Exception as e:
                last = e
                if attempt < 2:
                    time.sleep(delay)
        raise RuntimeError(f"tool {name} failed after retries: {last}") from last


def mcp_from_config() -> tuple[McpSession, dict]:
    cfg = load_json(spirl_config_path())
    mcp_url = str(cfg.get("api_base", "http://localhost:8000")).rstrip("/") + "/mcp"
    mcp_cfg = load_json(mcp_json_path())
    token = mcp_cfg["mcpServers"]["spirl"]["headers"]["Authorization"]
    return McpSession(mcp_url, token), cfg


def adr_root() -> Path:
    p = btc_root() / "external" / "architecture-decision-record"
    if not p.is_dir():
        raise SystemExit(f"Missing ADR clone: {p}")
    return p


def build_onboard_payload() -> tuple[list[str], dict[str, str]]:
    root = adr_root()
    tree: list[str] = []
    contents: dict[str, str] = {}

    def add(rel: str, path: Path) -> None:
        if not path.is_file():
            return
        raw = path.read_text(encoding="utf-8", errors="replace")[:MAX_CHARS_PER_FILE]
        contents[rel] = raw
        tree.append(rel)

    add("README.md", root / "README.md")
    add("CONTEXT.md", root / "CONTEXT.md")
    for md in sorted(root.glob("locales/en/examples/*/index.md"))[:18]:
        add(md.relative_to(root).as_posix(), md)
    for md in sorted(root.glob("locales/en/templates/decision-record-template-by-michael-nygard/index.md"))[:1]:
        add(md.relative_to(root).as_posix(), md)
    for md in sorted(root.glob("locales/en/templates/decision-record-template-of-the-madr-project/index.md"))[:1]:
        add(md.relative_to(root).as_posix(), md)
    if not contents:
        raise SystemExit("No ADR files collected for onboard.")
    return tree, contents


def persist_adr_project_id(project_id: str) -> None:
    cfg_path = spirl_config_path()
    cfg = load_json(cfg_path)
    cfg["adr_reference_project_id"] = project_id
    cfg.setdefault("projects", {})["paper3_adr_reference"] = project_id
    cfg_path.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")


def read_adr_project_id(cfg: dict) -> str:
    pid = (cfg.get("adr_reference_project_id") or "").strip()
    if pid:
        return pid
    proj = cfg.get("projects") or {}
    pid = str(proj.get("paper3_adr_reference") or "").strip()
    if pid:
        return pid
    raise SystemExit(
        "No ADR project UUID. Run --quickstart first or set "
        "adr_reference_project_id / projects.paper3_adr_reference in .spirl/config.json"
    )


def cmd_quickstart(mcp: McpSession) -> str:
    ctx_path = adr_root() / "CONTEXT.md"
    context_md = ctx_path.read_text(encoding="utf-8")[:40_000]
    # Small README excerpt only — large payloads cause Spirl quick_start to 504 (server timeout ~45s).
    readme = (adr_root() / "README.md").read_text(encoding="utf-8", errors="replace")[:12_000]
    context_md = context_md + "\n\n## README excerpt (truncated)\n\n" + readme

    result = mcp.call_tool(
        "quick_start",
        {
            "name": "ADR Reference Library (joelparkerhenderson)",
            "context_md": context_md,
            "enrich": False,
        },
    )
    save_last_response(result)
    if isinstance(result, str) and result.lower().startswith("error"):
        raise SystemExit(
            f"quick_start failed: {result[:500]}\n"
            "Retry with Spirl healthy, or create a project in the UI and set "
            "adr_reference_project_id in .spirl/config.json."
        )
    pid = find_uuid_in_obj(result)
    if not pid:
        raise SystemExit(
            "quick_start did not return a parseable project_id. "
            f"Inspect {research_dir() / 'adr_mcp_last_response.json'} and set UUID manually in config."
        )
    persist_adr_project_id(pid)
    print(f"quick_start OK — project_id={pid} (saved to .spirl/config.json)")
    return pid


def cmd_onboard(mcp: McpSession, project_id: str) -> None:
    tree, files = build_onboard_payload()
    result = mcp.call_tool(
        "onboard_existing_project",
        {
            "project_id": project_id,
            "file_tree": tree,
            "file_contents": files,
        },
    )
    save_last_response(result)
    print("onboard_existing_project submitted OK (see adr_mcp_last_response.json).")


def list_all_facts(mcp: McpSession, project_id: str) -> list[dict]:
    out: list[dict] = []
    offset = 0
    limit = 1000
    while True:
        page = mcp.call_tool(
            "list_facts_v1",
            {"project_id": project_id, "limit": limit, "offset": offset},
        )
        facts = page.get("facts") or []
        out.extend(facts)
        if len(facts) < limit:
            break
        offset += limit
    return out


def adr_paths() -> tuple[Path, Path]:
    r = research_dir()
    return (
        r / "paper3_checkpoints.experiment_ADR.jsonl",
        r / "paper3_execution_log.experiment_ADR.jsonl",
    )


def cmd_phases(mcp: McpSession, project_id: str) -> None:
    ckpt, log = adr_paths()
    agent = "adr_corpus_pipeline"
    exp = {"id": "ADR", "architecture_label": "adr_joelparkerhenderson_corpus", "dataset": "external/architecture-decision-record"}

    def checkpoint(phase: int, ctype: str, status: str, notes: str) -> None:
        append_jsonl(
            ckpt,
            {
                "timestamp": iso_now(),
                "phase": phase,
                "checkpoint_type": ctype,
                "agent_id": agent,
                "status": status,
                "experiment": exp,
                "notes": notes,
            },
        )

    def log_row(phase: int, action: str, result: dict) -> None:
        append_jsonl(
            log,
            {
                "timestamp": iso_now(),
                "phase": phase,
                "agent_id": agent,
                "action": action,
                "experiment": exp,
                "project": project_id,
                "result": result,
            },
        )

    rdir = research_dir()
    rdir.mkdir(parents=True, exist_ok=True)

    # Phase 1 — snapshot
    checkpoint(1, "phase_start", "in_progress", "ADR track Phase 1 — post-onboard snapshot")
    pm = mcp.call_tool("get_pm_context", {"project_id": project_id})
    log_row(1, "get_pm_context", {"ok": True, "keys": list(pm.keys()) if isinstance(pm, dict) else str(type(pm))})

    facts = list_all_facts(mcp, project_id)
    by_kind: dict[str, int] = {}
    for f in facts:
        k = str(f.get("kind") or "?")
        by_kind[k] = by_kind.get(k, 0) + 1
    log_row(1, "list_facts_v1_complete", {"count": len(facts), "by_kind": by_kind})

    edges = mcp.call_tool("list_fact_edges", {"project_id": project_id, "limit": 500})
    edge_list = edges.get("edges") or []
    log_row(1, "list_fact_edges", {"count": len(edge_list), "total": edges.get("total")})

    conflicts = mcp.call_tool("list_conflicts_v1", {"project_id": project_id, "limit": 200})
    cl = conflicts.get("conflicts") or []
    log_row(1, "list_conflicts_v1", {"count": len(cl)})

    try:
        metrics = mcp.call_tool("get_project_metrics_v1", {"project_id": project_id})
        log_row(1, "get_project_metrics_v1", {"returned": True, "summary": str(metrics)[:2000]})
    except Exception as e:
        log_row(1, "get_project_metrics_v1", {"error": str(e)})

    (rdir / "paper3_adr_phase1_report.md").write_text(
        f"# ADR corpus — Phase 1 snapshot\n\n"
        f"- **project_id:** `{project_id}`\n"
        f"- **facts:** {len(facts)} ({by_kind})\n"
        f"- **edges (first page):** {len(edge_list)}\n"
        f"- **conflicts listed:** {len(cl)}\n"
        f"- **time:** {iso_now()}\n",
        encoding="utf-8",
    )
    checkpoint(1, "phase_complete", "complete", "ADR Phase 1 snapshot written")

    # Phase 2 — observation (no synthetic injections)
    checkpoint(2, "phase_start", "in_progress", "ADR Phase 2 — conflict/health observation (no injection protocol)")
    log_row(
        2,
        "adr_phase2_placeholder",
        {
            "note": "Synthetic Paper 3 Phase 2 injections do not apply. This phase records post-onboard detector state only.",
            "conflict_count": len(cl),
        },
    )
    (rdir / "paper3_adr_phase2_report.md").write_text(
        "# ADR corpus — Phase 2 (observation)\n\n"
        "No `research.p3.*` ground-truth injections are run on the ADR track.\n\n"
        f"Conflict rows visible at end of Phase 1 pass: **{len(cl)}**.\n",
        encoding="utf-8",
    )
    checkpoint(2, "phase_complete", "complete", "ADR Phase 2 observation logged")

    # Phase 3 — metrics summary
    checkpoint(3, "phase_start", "in_progress", "ADR Phase 3 — aggregate metrics from MCP snapshot")
    log_row(
        3,
        "adr_metrics_summary",
        {"facts": len(facts), "edges_sample": len(edge_list), "conflicts": len(cl)},
    )
    (rdir / "paper3_adr_phase3_report.md").write_text(
        "# ADR corpus — Phase 3 (metrics)\n\n"
        f"| Metric | Value |\n|--------|------:|\n| Facts | {len(facts)} |\n| Edges (≤500 pull) | {len(edge_list)} |\n| Conflicts | {len(cl)} |\n",
        encoding="utf-8",
    )
    checkpoint(3, "phase_complete", "complete", "ADR Phase 3 report written")

    # Phase 4 — synthesis stub
    checkpoint(4, "phase_start", "in_progress", "ADR Phase 4 — narrative synthesis stub")
    log_row(4, "adr_phase4_stub", {"note": "Expand with qualitative ADR findings for paper discussion."})
    (rdir / "paper3_adr_phase4_report.md").write_text(
        "# ADR corpus — Phase 4 (synthesis)\n\n"
        "Use this section to tie **external validity** claims to the real markdown corpus.\n\n"
        "Suggested next steps: human review of extracted facts vs source files, error taxonomy, and "
        "comparison to synthetic Experiment C protocol.\n",
        encoding="utf-8",
    )
    checkpoint(4, "phase_complete", "complete", "ADR Phase 4 stub complete")

    print(f"Phases 1–4 logged to:\n  {ckpt}\n  {log}")


def main() -> None:
    ap = argparse.ArgumentParser(description="ADR corpus Spirl MCP pipeline")
    ap.add_argument("--quickstart", action="store_true", help="Run quick_start + save project UUID to config")
    ap.add_argument("--onboard", action="store_true", help="onboard_existing_project with EN ADR slice")
    ap.add_argument("--phases", action="store_true", help="Run read-only phases 1–4 (experiment_ADR logs)")
    ap.add_argument("--all", action="store_true", help="quickstart + onboard + phases (sequential)")
    ap.add_argument("--project-id", type=str, default="", help="Override project UUID for --onboard / --phases")
    args = ap.parse_args()

    if not (args.quickstart or args.onboard or args.phases or args.all):
        ap.print_help()
        sys.exit(2)

    mcp, cfg = mcp_from_config()
    mcp.connect()

    pid_override = args.project_id.strip()

    if args.all or args.quickstart:
        cmd_quickstart(mcp)
        cfg = load_json(spirl_config_path())

    project_id = pid_override or read_adr_project_id(cfg)

    if args.all or args.onboard:
        cmd_onboard(mcp, project_id)

    if args.all or args.phases:
        # Allow Aura time to index after onboard
        if args.all:
            print("Waiting 15s after onboard before snapshot…")
            time.sleep(15)
        cmd_phases(mcp, project_id)


if __name__ == "__main__":
    main()
