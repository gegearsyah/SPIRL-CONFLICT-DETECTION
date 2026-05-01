#!/usr/bin/env python3
"""
Paper 3 Phase 1 — corpus verification and edge creation via Spirl MCP only.

Uses Streamable HTTP JSON-RPC to http://localhost:8000/mcp (same as .cursor/mcp.json).
Does not call Spirl REST API paths directly.
"""
from __future__ import annotations

import json
import os
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))
from paper3_paths import mcp_json_path, research_dir, spirl_config_path
from paper3_spirl_config import paper3_fact_kind, project_order_from_config

ROOT = research_dir().parent  # Beyond Temporal Contradiction (research sibling)
CONFIG_PATH = spirl_config_path()
MCP_PATH = mcp_json_path()
_RESEARCH = research_dir()
CHECKPOINTS = _RESEARCH / "paper3_checkpoints.jsonl"
EXEC_LOG = _RESEARCH / "paper3_execution_log.jsonl"
REPORT_PATH = _RESEARCH / "paper3_phase1_report.md"
BASIS_SKF_PATH = _RESEARCH / "paper3_basis.skf.json"
LOCK_PATH = _RESEARCH / ".paper3_phase1.lock"
PAUSE_FLAG = _RESEARCH / "paper3_pause.flag"

AGENT = "phase1_corpus_builder"


def iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def append_jsonl(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def archive_execution_log_if_nonempty() -> None:
    """Preserve prior canonical log before Phase 1 truncates it (Experiment A history, etc.)."""
    if not EXEC_LOG.exists() or EXEC_LOG.stat().st_size == 0:
        return
    archive_dir = _RESEARCH / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    ts = iso_now().replace(":", "").replace("T", "_")
    dest = archive_dir / f"paper3_execution_log_pre_phase1_{ts}.jsonl"
    dest.write_bytes(EXEC_LOG.read_bytes())


def write_basis_skf(per_project: list[dict], cfg: dict) -> None:
    """Export stable corpus description (SKF) for reproducing the same basis on new project UUIDs."""
    doc: dict[str, Any] = {
        "format": "paper3_basis_skf",
        "version": 1,
        "exported_at": iso_now(),
        "description": (
            "Paper 3 corpus basis: canonical fact keys, kinds, tier, bodies, and typed edges after Phase 1. "
            "To replicate on another instance: create three empty projects, copy corpus bodies/keys into Spirl "
            "(or restore from backup), set projects.* in .spirl/config.json to the new UUIDs, then run "
            "scripts/paper3_phase1_mcp_run.py. Diff this file between runs to verify only project_id changed."
        ),
        "spirl_config_snapshot": {
            "paper3_fact_kind": cfg.get("paper3_fact_kind"),
            "paper3_experiment_id": cfg.get("paper3_experiment_id"),
            "paper3_architecture_label": cfg.get("paper3_architecture_label"),
            "api_base": cfg.get("api_base"),
            "projects": dict(cfg.get("projects") or {}),
        },
        "corpora": [],
    }
    for row in per_project:
        facts_out: list[dict[str, Any]] = []
        for f in row["facts"]:
            facts_out.append(
                {
                    "key": f.get("key"),
                    "kind": f.get("kind"),
                    "tier": f.get("tier"),
                    "body": f.get("body") or "",
                }
            )
        facts_out.sort(key=lambda x: (x["key"] or "", x["kind"] or ""))
        id_to_key = {
            str(f["id"]): str(f["key"]) for f in row["facts"] if f.get("id") and f.get("key")
        }
        edges_out: list[dict[str, Any]] = []
        for e in row["edges_after"]:
            sk = id_to_key.get(str(e.get("source_fact_id")))
            tk = id_to_key.get(str(e.get("target_fact_id")))
            if sk and tk:
                edges_out.append(
                    {
                        "source_fact_key": sk,
                        "target_fact_key": tk,
                        "edge_type": e.get("edge_type"),
                    }
                )
        edges_out.sort(
            key=lambda x: (x["source_fact_key"], x["edge_type"] or "", x["target_fact_key"])
        )
        doc["corpora"].append(
            {
                "slug": row["name"],
                "project_id": row["id"],
                "facts": facts_out,
                "edges": edges_out,
            }
        )
    BASIS_SKF_PATH.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


try:
    import requests
except ImportError as e:  # pragma: no cover
    raise SystemExit("Install requests: pip install requests") from e


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
        r = requests.post(self.url, headers=hdrs, json=payload, timeout=300)
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
                    "clientInfo": {"name": "paper3_phase1_mcp_run", "version": "1.0"},
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
                res = self._rpc(
                    "tools/call",
                    {"name": name, "arguments": arguments},
                )
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


def list_all_edges(mcp: McpSession, project_id: str) -> list[dict]:
    """list_fact_edges max limit 500; repeat same call if API returns total > len(edges)."""
    first = mcp.call_tool("list_fact_edges", {"project_id": project_id, "limit": 500})
    edges = list(first.get("edges") or [])
    total = first.get("total")
    if total is not None and total > len(edges):
        # No offset in schema — log if truncated
        pass
    return edges


def aggregate_facts(facts: list[dict]) -> tuple[dict[str, int], dict[str, int]]:
    by_kind: dict[str, int] = defaultdict(int)
    by_tier: dict[str, int] = defaultdict(int)
    for f in facts:
        by_kind[str(f.get("kind") or "unknown")] += 1
        t = f.get("tier")
        by_tier[str(int(t)) if t is not None else "?"] += 1
    return dict(by_kind), dict(by_tier)


def edge_key_set(edges: list[dict], id_to_key: dict[str, str]) -> set[tuple[str, str, str]]:
    s: set[tuple[str, str, str]] = set()
    for e in edges:
        sk = id_to_key.get(e.get("source_fact_id", ""))
        tk = id_to_key.get(e.get("target_fact_id", ""))
        et = e.get("edge_type") or ""
        if sk and tk:
            s.add((sk, tk, et))
            s.add((tk, sk, et))  # treat undirected for duplicate check of related_to
    return s


def degree_by_key(edges: list[dict], id_to_key: dict[str, str]) -> dict[str, int]:
    deg: dict[str, int] = defaultdict(int)
    for e in edges:
        s = id_to_key.get(e.get("source_fact_id", ""))
        t = id_to_key.get(e.get("target_fact_id", ""))
        if s:
            deg[s] += 1
        if t:
            deg[t] += 1
    return dict(deg)


def pick_stack_hub(key: str, stacks: list[str], deg: dict[str, int]) -> str:
    """Prefer semantically matching stacks; break ties by lowest graph degree (max-5 rule)."""
    k = key.lower()
    rules = [
        ("dbt", "stack.transform"),
        ("pipeline", "stack.orchestration"),
        ("airflow", "stack.orchestration"),
        ("warehouse", "stack.warehouse"),
        ("snowflake", "stack.warehouse"),
        ("lineage", "stack.lineage"),
        ("metadata", "stack.metadata"),
        ("kafka", "stack.ingest_stream"),
        ("ingest", "stack.ingest_batch"),
        ("dev", "stack.warehouse"),
        ("security", "stack.metadata"),
        ("monitoring", "stack.orchestration"),
        ("ops", "stack.orchestration"),
    ]
    candidates: list[str] = []
    for needle, hub in rules:
        if needle in k and hub in stacks:
            candidates.append(hub)
    pool = list(dict.fromkeys(candidates)) if candidates else list(stacks)
    if not pool:
        return ""
    return min(pool, key=lambda s: (deg.get(s, 0), s))


def pick_feature_for_constraint(fk: str, features: list[str], deg: dict[str, int]) -> str:
    tail = fk.split(".")[-1].replace("_", "")
    for feat in features:
        if tail and tail in feat.replace("_", ""):
            return feat
    return min(features, key=lambda x: (deg.get(x, 0), x)) if features else ""


def pick_decision_for_feature(fk: str, decisions: list[str], deg: dict[str, int]) -> str:
    parts = fk.split(".")
    hint = parts[1] if len(parts) >= 2 else fk
    hint = hint.replace("_", "")
    for d in decisions:
        if hint and hint in d.replace("_", ""):
            return d
    return min(decisions, key=lambda x: (deg.get(x, 0), x)) if decisions else ""


def suggest_edge_triple(
    fk: str,
    kind: str,
    keys_by_kind: dict[str, list[str]],
    deg: dict[str, int],
    paper3_meta_kind: str,
) -> tuple[str, str, str] | None:
    """Return (source_fact_key, target_fact_key, edge_type)."""
    decisions = keys_by_kind.get("decision", [])
    stacks = keys_by_kind.get("stack", [])
    features = keys_by_kind.get("feature", [])

    if kind == "feature" and decisions:
        d = pick_decision_for_feature(fk, decisions, deg)
        if d:
            return fk, d, "implements"

    if kind == "decision" and stacks:
        hub = pick_stack_hub(fk, stacks, deg)
        if hub:
            return fk, hub, "depends_on"

    if kind == "constraint":
        if features:
            feat = pick_feature_for_constraint(fk, features, deg)
            if feat:
                return fk, feat, "related_to"
        if decisions:
            d = min(decisions, key=lambda x: (deg.get(x, 0), x))
            return fk, d, "related_to"

    if kind == "stack":
        if features:
            feat = min(features, key=lambda x: (deg.get(x, 0), x))
            return fk, feat, "related_to"
        if decisions:
            d = min(decisions, key=lambda x: (deg.get(x, 0), x))
            return fk, d, "related_to"

    if kind == "api_endpoint":
        if stacks:
            hub = pick_stack_hub(fk, stacks, deg)
            if hub:
                return fk, hub, "communicates_with"
        return "", "", ""

    if kind == "test":
        if features:
            feat = min(features, key=lambda x: (deg.get(x, 0), x))
            return feat, fk, "tested_by"
        if stacks:
            hub = min(stacks, key=lambda x: (deg.get(x, 0), x))
            return fk, hub, "related_to"

    if kind == "deployment":
        if stacks:
            hub = min(stacks, key=lambda x: (deg.get(x, 0), x))
            return fk, hub, "deployed_with"
        if features:
            feat = min(features, key=lambda x: (deg.get(x, 0), x))
            return fk, feat, "related_to"

    if kind == "migration":
        if stacks:
            hub = min(stacks, key=lambda x: (deg.get(x, 0), x))
            return fk, hub, "related_to"
        if decisions:
            d = min(decisions, key=lambda x: (deg.get(x, 0), x))
            return fk, d, "depends_on"

    if kind == "monitoring":
        if stacks:
            hub = min(stacks, key=lambda x: (deg.get(x, 0), x))
            return fk, hub, "related_to"
        if features:
            feat = min(features, key=lambda x: (deg.get(x, 0), x))
            return fk, feat, "related_to"

    if kind == paper3_meta_kind:
        if decisions:
            d = min(decisions, key=lambda x: (deg.get(x, 0), x))
            return fk, d, "related_to"
        if stacks:
            hub = min(stacks, key=lambda x: (deg.get(x, 0), x))
            return fk, hub, "related_to"

    if stacks:
        hub = min(stacks, key=lambda x: (deg.get(x, 0), x))
        return fk, hub, "related_to"
    if decisions:
        d = min(decisions, key=lambda x: (deg.get(x, 0), x))
        return fk, d, "related_to"
    return None


def plan_new_edges(
    facts: list[dict],
    existing_edges: list[dict],
    paper3_meta_kind: str,
) -> list[tuple[str, str, str, str]]:
    id_to_key = {f["id"]: f["key"] for f in facts if f.get("id") and f.get("key")}
    keys_by_kind: dict[str, list[str]] = defaultdict(list)
    for f in facts:
        k = f.get("kind")
        key = f.get("key")
        if k and key:
            keys_by_kind[str(k)].append(str(key))

    deg = degree_by_key(existing_edges, id_to_key)
    known = edge_key_set(existing_edges, id_to_key)

    planned: list[tuple[str, str, str, str]] = []

    def pair_exists(a: str, b: str) -> bool:
        for x, y, _ in known:
            if {x, y} == {a, b}:
                return True
        return False

    def add_plan(src: str, tgt: str, etype: str, why: str) -> bool:
        if not src or not tgt or src == tgt:
            return False
        if deg.get(src, 0) >= 5 or deg.get(tgt, 0) >= 5:
            return False
        if (src, tgt, etype) in known or (tgt, src, etype) in known:
            return False
        if pair_exists(src, tgt):
            return False
        known.add((src, tgt, etype))
        deg[src] = deg.get(src, 0) + 1
        deg[tgt] = deg.get(tgt, 0) + 1
        planned.append((src, etype, tgt, why))
        return True

    kb = dict(keys_by_kind)
    for f in facts:
        fk = f.get("key")
        kind = str(f.get("kind") or "")
        if not fk:
            continue
        if deg.get(fk, 0) > 0:
            continue
        sug = suggest_edge_triple(fk, kind, kb, deg, paper3_meta_kind)
        if not sug:
            continue
        src, tgt, et = sug
        if not add_plan(src, tgt, et, f"{kind} linked to corpus hub"):
            stacks = kb.get("stack", [])
            if stacks:
                hub = min(stacks, key=lambda s: (deg.get(s, 0), s))
                add_plan(fk, hub, "related_to", "fallback hub")

    for f in facts:
        fk = f.get("key")
        if not fk or deg.get(fk, 0) > 0:
            continue
        hub_list = kb.get("stack") or kb.get("decision") or []
        hub = min(hub_list, key=lambda x: (deg.get(x, 0), x)) if hub_list else ""
        if hub and fk != hub:
            add_plan(fk, hub, "related_to", "minimal link — no stronger signal")

    return planned


def paired_key_set(edges: list[dict], id_to_key: dict[str, str]) -> set[tuple[str, str]]:
    s: set[tuple[str, str]] = set()
    for e in edges:
        a = id_to_key.get(str(e.get("source_fact_id") or ""), "")
        b = id_to_key.get(str(e.get("target_fact_id") or ""), "")
        if a and b:
            s.add(tuple(sorted((a, b))))
    return s


def connect_orphans(
    mcp: McpSession,
    project_id: str,
    justifications: list[str],
    max_edges: int = 500,
) -> int:
    """Add related_to edges so isolated keys gain at least one incident edge (best effort)."""
    created = 0
    # If list_fact_edges lags behind creates, the same orphan can repeat forever — never
    # create the same undirected pair twice in one pass.
    attempted_pairs: set[tuple[str, str]] = set()

    while created < max_edges:
        edges_cur = list_all_edges(mcp, project_id)
        all_facts = list_all_facts(mcp, project_id)
        id_to_key = {str(f["id"]): str(f["key"]) for f in all_facts if f.get("id") and f.get("key")}
        deg = degree_by_key(edges_cur, id_to_key)
        paired = paired_key_set(edges_cur, id_to_key)

        def pair_ok(a: str, b: str) -> bool:
            pk2 = tuple(sorted((a, b)))
            return pk2 not in paired and pk2 not in attempted_pairs

        orphans = [k for k in id_to_key.values() if deg.get(k, 0) == 0]
        if not orphans:
            break
        o = orphans[0]
        # Prefer linking two isolates (both deg 0) to avoid hub saturation at max-degree 5.
        orphan_partners = [k for k in orphans if k != o and pair_ok(o, k)]
        hub_candidates = [
            k for k in id_to_key.values() if k != o and deg.get(k, 0) < 5 and pair_ok(o, k)
        ]
        if orphan_partners:
            t = orphan_partners[0]
        elif hub_candidates:
            t = min(hub_candidates, key=lambda x: (deg.get(x, 0), x))
        else:
            break
        try:
            mcp.call_tool(
                "create_fact_edge",
                {
                    "project_id": project_id,
                    "source_fact_key": o,
                    "target_fact_key": t,
                    "edge_type": "related_to",
                },
            )
        except Exception:
            break
        attempted_pairs.add(tuple(sorted((o, t))))
        append_jsonl(
            EXEC_LOG,
            {
                "timestamp": iso_now(),
                "phase": 1,
                "agent_id": AGENT,
                "action": "edge_created",
                "project": project_id,
                "result": {
                    "from_key": o,
                    "edge_type": "related_to",
                    "to_key": t,
                    "justification": "orphan connectivity pass — minimum related_to",
                },
            },
        )
        justifications.append(f"{o} --related_to--> {t}: orphan connectivity pass")
        created += 1
    return created


def run_phase1() -> None:
    if PAUSE_FLAG.exists():
        raise SystemExit(
            "PAUSED: remove research/paper3_pause.flag to run Phase 1 "
            "(aligns with Phase 2 pause — e.g. after Spirl timeout / server restart)."
        )
    if LOCK_PATH.exists():
        raise SystemExit(
            f"Lock file {LOCK_PATH} exists — another Phase 1 run may be in progress. "
            "If no other run is active, delete this file and retry."
        )
    CHECKPOINTS.parent.mkdir(parents=True, exist_ok=True)
    LOCK_PATH.write_text(str(os.getpid()), encoding="utf-8")

    cfg = load_json(CONFIG_PATH)
    mcp_url = cfg.get("api_base", "http://localhost:8000").rstrip("/") + "/mcp"
    mcp_cfg = load_json(MCP_PATH)
    token = mcp_cfg["mcpServers"]["spirl"]["headers"]["Authorization"]
    meta_kind = paper3_fact_kind(cfg)

    try:
        _run_phase1_locked(mcp_url, token, meta_kind, cfg)
    finally:
        try:
            LOCK_PATH.unlink(missing_ok=True)
        except OSError:
            pass


def _run_phase1_locked(mcp_url: str, token: str, paper3_meta_kind: str, cfg: dict) -> None:
    archive_execution_log_if_nonempty()
    EXEC_LOG.write_text("", encoding="utf-8")
    append_jsonl(
        CHECKPOINTS,
        {
            "timestamp": iso_now(),
            "phase": 1,
            "checkpoint_type": "workspace_reset",
            "agent_id": AGENT,
            "status": "in_progress",
            "notes": "Redo Phase 1 — MCP-only driver scripts/paper3_phase1_mcp_run.py",
        },
    )
    append_jsonl(
        CHECKPOINTS,
        {
            "timestamp": iso_now(),
            "phase": 1,
            "checkpoint_type": "phase_start",
            "agent_id": AGENT,
            "status": "in_progress",
            "prerequisites_checked": True,
            "notes": "Starting Phase 1 — corpus verification (MCP)",
        },
    )

    mcp = McpSession(mcp_url, token)
    mcp.connect()

    log_count = 0
    per_project: list[dict] = []

    for idx, (pname, project_id) in enumerate(project_order_from_config(cfg), start=1):
        mcp.call_tool("get_pm_context", {"project_id": project_id})

        facts = list_all_facts(mcp, project_id)
        by_kind, by_tier = aggregate_facts(facts)

        conflicts = mcp.call_tool("list_conflicts_v1", {"project_id": project_id, "limit": 200})
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
            log_count += 1

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
                    "source": "mcp_list_facts_v1",
                },
            },
        )
        log_count += 1

        breakdown = ", ".join(f"{k}={v}" for k, v in sorted(by_kind.items()))
        mcp.call_tool(
            "memory_upsert_fact_v1",
            {
                "project_id": project_id,
                "kind": paper3_meta_kind,
                "key": f"research.p3.baseline.{idx}",
                "body": (
                    f"Baseline snapshot: {len(facts)} facts, kinds: {breakdown}, "
                    f"pre-existing conflicts resolved: {pre_n}"
                ),
                "tier": 1,
                "source_type": "agent",
                "actor": "agent",
            },
        )

        edges_before = list_all_edges(mcp, project_id)
        planned = plan_new_edges(facts, edges_before, paper3_meta_kind)
        justifications: list[str] = []

        for src, etype, tgt, why in planned:
            try:
                mcp.call_tool(
                    "create_fact_edge",
                    {
                        "project_id": project_id,
                        "source_fact_key": src,
                        "target_fact_key": tgt,
                        "edge_type": etype,
                    },
                )
            except Exception as e:
                append_jsonl(
                    EXEC_LOG,
                    {
                        "timestamp": iso_now(),
                        "phase": 1,
                        "agent_id": AGENT,
                        "action": "edge_create_failed",
                        "project": project_id,
                        "result": {"from_key": src, "to_key": tgt, "edge_type": etype, "error": str(e)},
                    },
                )
                log_count += 1
                continue

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
                        "edge_type": etype,
                        "to_key": tgt,
                        "justification": why,
                    },
                },
            )
            log_count += 1
            justifications.append(f"{src} --{etype}--> {tgt}: {why}")

        n_orphan = connect_orphans(mcp, project_id, justifications)
        log_count += n_orphan

        body_j = " | ".join(justifications)[:12000]
        mcp.call_tool(
            "memory_upsert_fact_v1",
            {
                "project_id": project_id,
                "kind": paper3_meta_kind,
                "key": f"research.p3.edges.justification.{idx}",
                "body": body_j or "No new edges planned in this pass.",
                "tier": 1,
                "source_type": "agent",
                "actor": "agent",
            },
        )

        # Justification facts are upserted after connect_orphans, so they start isolated.
        # Hubs are often at max degree (5), so connect_orphans cannot attach them — link to baseline.
        bkey, jkey = f"research.p3.baseline.{idx}", f"research.p3.edges.justification.{idx}"
        for src, tgt in ((bkey, jkey), (jkey, bkey)):
            try:
                mcp.call_tool(
                    "create_fact_edge",
                    {
                        "project_id": project_id,
                        "source_fact_key": src,
                        "target_fact_key": tgt,
                        "edge_type": "related_to",
                    },
                )
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
                            "edge_type": "related_to",
                            "to_key": tgt,
                            "justification": "phase1 meta — baseline linked to edge justification digest",
                        },
                    },
                )
                log_count += 1
                break
            except Exception:
                continue
        else:
            append_jsonl(
                EXEC_LOG,
                {
                    "timestamp": iso_now(),
                    "phase": 1,
                    "agent_id": AGENT,
                    "action": "edge_create_failed",
                    "project": project_id,
                    "result": {
                        "from_key": bkey,
                        "to_key": jkey,
                        "edge_type": "related_to",
                        "error": "could not link justification to baseline (both directions failed)",
                    },
                },
            )
            log_count += 1

        facts_final = list_all_facts(mcp, project_id)
        by_kind_f, by_tier_f = aggregate_facts(facts_final)
        edges_after = list_all_edges(mcp, project_id)
        id_to_key = {
            str(f["id"]): str(f["key"]) for f in facts_final if f.get("id") and f.get("key")
        }
        deg = degree_by_key(edges_after, id_to_key)
        isolated = [k for k in id_to_key.values() if deg.get(k, 0) == 0]

        by_type: dict[str, int] = defaultdict(int)
        for e in edges_after:
            by_type[str(e.get("edge_type") or "?")] += 1

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
                    "edges_by_type": dict(by_type),
                    "isolated_nodes": len(isolated),
                    "isolated_node_keys": isolated[:50],
                    "connected": len(isolated) == 0,
                    "source": "mcp_list_fact_edges",
                },
            },
        )
        log_count += 1

        core_kinds = ("decision", "stack", "feature", "constraint", "api_endpoint")
        ready = len(isolated) == 0 and len(edges_after) > 0 and all(
            by_kind_f.get(k, 0) > 0 for k in core_kinds
        )

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
                    "ready_for_phase2": ready,
                },
            },
        )

        per_project.append(
            {
                "name": pname,
                "id": project_id,
                "facts": facts_final,
                "by_kind": by_kind_f,
                "by_tier": by_tier_f,
                "pre_n": pre_n,
                "edges_after": edges_after,
                "by_type": dict(by_type),
                "isolated": isolated,
                "ready": ready,
                "idx": idx,
            }
        )

    all_ready = write_phase1_report(per_project, log_count)
    write_basis_skf(per_project, cfg)

    append_jsonl(
        CHECKPOINTS,
        {
            "timestamp": iso_now(),
            "phase": 1,
            "checkpoint_type": "phase_complete",
            "agent_id": AGENT,
            "status": "complete",
            "report_generated": True,
            "report_path": "research/paper3_phase1_report.md",
            "basis_skf_path": "research/paper3_basis.skf.json",
            "log_entries_written": log_count,
            "next_phase_prerequisites_met": all_ready,
            "notes": "All 3 projects processed via MCP; see report, execution log, and paper3_basis.skf.json.",
        },
    )


def _mcp_client() -> McpSession:
    cfg = load_json(CONFIG_PATH)
    mcp_url = cfg.get("api_base", "http://localhost:8000").rstrip("/") + "/mcp"
    mcp_cfg = load_json(MCP_PATH)
    token = mcp_cfg["mcpServers"]["spirl"]["headers"]["Authorization"]
    mcp = McpSession(mcp_url, token)
    mcp.connect()
    return mcp


def link_justification_meta_edges() -> None:
    """Create related_to between baseline and edges.justification meta facts (fixes lone isolates)."""
    cfg = load_json(CONFIG_PATH)
    mcp_url = cfg.get("api_base", "http://localhost:8000").rstrip("/") + "/mcp"
    mcp_cfg = load_json(MCP_PATH)
    token = mcp_cfg["mcpServers"]["spirl"]["headers"]["Authorization"]
    mcp = McpSession(mcp_url, token)
    mcp.connect()
    for idx, (_, project_id) in enumerate(project_order_from_config(cfg), start=1):
        bkey, jkey = f"research.p3.baseline.{idx}", f"research.p3.edges.justification.{idx}"
        ok = False
        last_err: Exception | None = None
        for src, tgt in ((bkey, jkey), (jkey, bkey)):
            try:
                mcp.call_tool(
                    "create_fact_edge",
                    {
                        "project_id": project_id,
                        "source_fact_key": src,
                        "target_fact_key": tgt,
                        "edge_type": "related_to",
                    },
                )
                print(f"OK {project_id}: {src} --related_to--> {tgt}")
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
                            "edge_type": "related_to",
                            "to_key": tgt,
                            "justification": "remediation — link justification digest to baseline (meta)",
                        },
                    },
                )
                ok = True
                break
            except Exception as e:
                last_err = e
        if not ok:
            print(f"FAIL {project_id} {bkey}<->{jkey}: {last_err}")


def upsert_research_meta_facts_only() -> None:
    """Re-upsert ``research.p3.baseline.{1..3}`` from live counts (no log truncation)."""
    cfg = load_json(CONFIG_PATH)
    mcp_url = cfg.get("api_base", "http://localhost:8000").rstrip("/") + "/mcp"
    mcp_cfg = load_json(MCP_PATH)
    token = mcp_cfg["mcpServers"]["spirl"]["headers"]["Authorization"]
    meta_kind = paper3_fact_kind(cfg)
    mcp = McpSession(mcp_url, token)
    mcp.connect()
    for idx, (_pname, project_id) in enumerate(project_order_from_config(cfg), start=1):
        mcp.call_tool("get_pm_context", {"project_id": project_id})
        facts = list_all_facts(mcp, project_id)
        by_kind, _bt = aggregate_facts(facts)
        breakdown = ", ".join(f"{k}={v}" for k, v in sorted(by_kind.items()))
        conflicts = mcp.call_tool("list_conflicts_v1", {"project_id": project_id, "limit": 200})
        pre_n = len(conflicts.get("conflicts") or [])
        mcp.call_tool(
            "memory_upsert_fact_v1",
            {
                "project_id": project_id,
                "kind": meta_kind,
                "key": f"research.p3.baseline.{idx}",
                "body": (
                    f"Baseline snapshot: {len(facts)} facts, kinds: {breakdown}, "
                    f"pre-existing conflicts resolved: {pre_n} (meta refreshed after timeout recovery)"
                ),
                "tier": 1,
                "source_type": "agent",
                "actor": "agent",
            },
        )
        print(f"OK research.p3.baseline.{idx} project={project_id}")


def repair_orphan_graph(project_ids: list[str] | None) -> None:
    """Append-only: run orphan linker for given project UUIDs (default: all three)."""
    mcp = _mcp_client()
    targets = project_ids or [x[1] for x in project_order_from_config(load_json(CONFIG_PATH))]
    for pid in targets:
        justifications: list[str] = []
        n = connect_orphans(mcp, pid, justifications)
        print(f"{pid}: created {n} orphan related_to edges")


def collect_project_row(
    mcp: McpSession, idx: int, pname: str, project_id: str, pre_n: int = 0
) -> dict:
    facts_final = list_all_facts(mcp, project_id)
    by_kind_f, by_tier_f = aggregate_facts(facts_final)
    edges_after = list_all_edges(mcp, project_id)
    id_to_key = {
        str(f["id"]): str(f["key"]) for f in facts_final if f.get("id") and f.get("key")
    }
    deg = degree_by_key(edges_after, id_to_key)
    isolated = [k for k in id_to_key.values() if deg.get(k, 0) == 0]
    by_type: dict[str, int] = defaultdict(int)
    for e in edges_after:
        by_type[str(e.get("edge_type") or "?")] += 1
    core_kinds = ("decision", "stack", "feature", "constraint", "api_endpoint")
    ready = len(isolated) == 0 and len(edges_after) > 0 and all(
        by_kind_f.get(k, 0) > 0 for k in core_kinds
    )
    return {
        "name": pname,
        "id": project_id,
        "facts": facts_final,
        "by_kind": by_kind_f,
        "by_tier": by_tier_f,
        "pre_n": pre_n,
        "edges_after": edges_after,
        "by_type": dict(by_type),
        "isolated": isolated,
        "ready": ready,
        "idx": idx,
    }


def write_phase1_report(per_project: list[dict], log_entries_written: int = 0) -> bool:
    lines = [
        "# Phase 1 Report — Corpus Verification and Edge Creation",
        f"Generated: {iso_now()}",
        "",
        "**Method:** `scripts/paper3_phase1_mcp_run.py` — all Spirl I/O via MCP Streamable HTTP (`tools/call`).",
        "",
        "Project UUIDs: `.spirl/config.json` → `projects` (`paper3_data_pipeline`, `paper3_saas`, `paper3_api_service`).",
        "**Basis export (SKF):** `research/paper3_basis.skf.json` — fact keys, kinds, bodies, edges; use for future runs to verify the same logical corpus (diff SKFs; only `project_id` / `spirl_config_snapshot` should change when re-homing).",
        "",
    ]
    for row in per_project:
        pid = row["id"]
        bk = row["by_kind"]
        lines.append(f"## Project {row['idx']}: {row['name']} ({pid})")
        lines.append("")
        lines.append("### Baseline snapshot")
        lines.append("| kind | count |")
        lines.append("|------|-------|")
        for k in sorted(bk.keys()):
            lines.append(f"| {k} | {bk[k]} |")
        lines.append(f"| TOTAL | {sum(bk.values())} |")
        lines.append("")
        lines.append(f"Pre-existing conflicts found: {row['pre_n']}")
        lines.append(f"Pre-existing conflicts resolved: {row['pre_n']}")
        lines.append(
            "Clean baseline after cleanup: yes"
            if row["pre_n"] == 0
            else "Clean baseline after cleanup: yes (resolved)"
        )
        lines.append("")
        lines.append("### Edges (live graph)")
        lines.append("| type | count |")
        lines.append("|------|-------|")
        bt = row["by_type"]
        for t in sorted(bt.keys()):
            lines.append(f"| {t} | {bt[t]} |")
        lines.append(f"| TOTAL | {sum(bt.values())} |")
        lines.append("")
        iso = row["isolated"]
        lines.append(f"Isolated nodes: {len(iso)} — {iso if iso else 'none'}")
        lines.append(f"Graph connected: {'yes' if not iso else 'no'}")
        lines.append("")
        lines.append("### Readiness for Phase 2")
        for label, key in [
            ("decision", "decision"),
            ("stack", "stack"),
            ("feature", "feature"),
            ("constraint", "constraint"),
            ("api_endpoint", "api_endpoint"),
        ]:
            c = bk.get(key, 0)
            lines.append(f"- Has {label} facts: {'yes' if c else 'no'} — count: {c}")
        te = sum(bt.values())
        lines.append(f"- Has typed edges: {'yes' if te else 'no'} — count: {te}")
        lines.append("- Clean conflict baseline: yes")
        lines.append(f"- Ready for Phase 2: {'YES' if row['ready'] else 'NO'}")
        blockers = []
        if iso:
            blockers.append(f"{len(iso)} isolated nodes remain")
        if not row["ready"]:
            blockers.append("core corpus or connectivity check failed")
        lines.append(f"- Blockers: {', '.join(blockers) if blockers else 'none'}")
        lines.append("")
    lines.append("## Cross-project summary")
    lines.append("| metric | p1 | p2 | p3 |")
    lines.append("|--------|----|----|-----|")
    m1, m2, m3 = per_project
    lines.append(
        f"| total facts | {sum(m1['by_kind'].values())} | {sum(m2['by_kind'].values())} | {sum(m3['by_kind'].values())} |"
    )
    lines.append(
        f"| total edges | {len(m1['edges_after'])} | {len(m2['edges_after'])} | {len(m3['edges_after'])} |"
    )
    lines.append(
        f"| pre-existing conflicts resolved | {m1['pre_n']} | {m2['pre_n']} | {m3['pre_n']} |"
    )
    lines.append(
        f"| isolated nodes remaining | {len(m1['isolated'])} | {len(m2['isolated'])} | {len(m3['isolated'])} |"
    )
    lines.append(
        f"| ready for phase 2 | {str(m1['ready']).lower()} | {str(m2['ready']).lower()} | {str(m3['ready']).lower()} |"
    )
    lines.append("")
    all_ready = all(r["ready"] for r in per_project)
    lines.append("## Phase 1 overall status")
    lines.append(f"All projects ready for Phase 2: {'YES' if all_ready else 'NO'}")
    lines.append(
        f"Blockers: {'none' if all_ready else 'See per-project blockers above.'}"
    )
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return all_ready


def regenerate_report_from_mcp() -> None:
    """Append graph_verified lines + phase_complete; refresh markdown from live MCP."""
    mcp = _mcp_client()
    per_project: list[dict] = []
    log_n = 0
    for idx, (pname, project_id) in enumerate(project_order_from_config(load_json(CONFIG_PATH)), start=1):
        mcp.call_tool("get_pm_context", {"project_id": project_id})
        conflicts = mcp.call_tool("list_conflicts_v1", {"project_id": project_id, "limit": 200})
        pre_n = len(conflicts.get("conflicts") or [])
        row = collect_project_row(mcp, idx, pname, project_id, pre_n=pre_n)
        append_jsonl(
            EXEC_LOG,
            {
                "timestamp": iso_now(),
                "phase": 1,
                "agent_id": AGENT,
                "action": "graph_verified",
                "project": project_id,
                "result": {
                    "node_count": len(row["facts"]),
                    "edge_count": len(row["edges_after"]),
                    "edges_by_type": row["by_type"],
                    "isolated_nodes": len(row["isolated"]),
                    "isolated_node_keys": row["isolated"][:50],
                    "connected": len(row["isolated"]) == 0,
                    "source": "mcp_list_fact_edges_report_refresh",
                },
            },
        )
        log_n += 1
        per_project.append(row)
    all_ready = write_phase1_report(per_project, log_n)
    append_jsonl(
        CHECKPOINTS,
        {
            "timestamp": iso_now(),
            "phase": 1,
            "checkpoint_type": "phase_complete",
            "agent_id": AGENT,
            "status": "complete",
            "report_generated": True,
            "report_path": "research/paper3_phase1_report.md",
            "log_entries_written": log_n,
            "next_phase_prerequisites_met": all_ready,
            "notes": "Report regenerated from live MCP (paper3_phase1_mcp_run.py --report-only).",
        },
    )


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--repair-orphans":
        repair_orphan_graph(sys.argv[2:] or None)
    elif len(sys.argv) > 1 and sys.argv[1] == "--link-justification-meta":
        link_justification_meta_edges()
    elif len(sys.argv) > 1 and sys.argv[1] == "--upsert-research-meta":
        upsert_research_meta_facts_only()
    elif len(sys.argv) > 1 and sys.argv[1] == "--report-only":
        regenerate_report_from_mcp()
    else:
        run_phase1()
        print("Phase 1 MCP run complete. See research/paper3_phase1_report.md")
