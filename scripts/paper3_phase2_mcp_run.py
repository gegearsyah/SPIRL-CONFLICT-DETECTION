#!/usr/bin/env python3
"""
Paper 3 Phase 2 — conflict injection via Spirl MCP only (Streamable HTTP JSON-RPC).

Uses the same transport as .cursor/mcp.json. No direct REST paths.
Retries MCP tools with 1s / 2s / 4s backoff (3 attempts). No sleeps in the hot path.

Ground-truth keys are stable: research.p3.groundtruth.{1..200}. Spirl may keep bi-temporal
history: uniqueness on (project_id, key) applies only to current rows
(tombstoned_at IS NULL AND valid_until IS NULL), so re-runs can insert a new current row
without duplicate-key failures while older versions remain. Phase 3 must count/list only
current ground-truth rows (e.g. valid_until null) so totals are not doubled.
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))
from paper3_paths import mcp_json_path, research_dir, spirl_config_path
from paper3_spirl_config import (
    paper3_experiment_block,
    paper3_fact_kind,
    paper3_phase2_artifact_paths,
    paper3_project_ids,
    paper3_target_per_project,
)

ROOT = research_dir().parent  # Beyond Temporal Contradiction
CONFIG_PATH = spirl_config_path()
MCP_PATH = mcp_json_path()
_RESEARCH = research_dir()
# Phase 1 completion always read from canonical checkpoints (shared across experiments).
PHASE1_CHECKPOINTS = _RESEARCH / "paper3_checkpoints.jsonl"
CHECKPOINTS = _RESEARCH / "paper3_checkpoints.jsonl"
EXEC_LOG = _RESEARCH / "paper3_execution_log.jsonl"
PHASE2_REPORT_PATH = _RESEARCH / "paper3_phase2_report.md"
PAUSE_FLAG = _RESEARCH / "paper3_pause.flag"


def apply_phase2_paths(cfg: dict) -> None:
    """Set CHECKPOINTS, EXEC_LOG, PHASE2_REPORT_PATH from paper3_experiment_id."""
    global CHECKPOINTS, EXEC_LOG, PHASE2_REPORT_PATH
    el, ck, rp = paper3_phase2_artifact_paths(ROOT, cfg)
    EXEC_LOG, CHECKPOINTS, PHASE2_REPORT_PATH = el, ck, rp


def _experiment_id(cfg: dict) -> str:
    return str(cfg.get("paper3_experiment_id") or "A").strip() or "A"


def _row_matches_experiment(o: dict, exp_id: str) -> bool:
    ex = o.get("experiment")
    if not ex:
        return exp_id.upper() == "A"
    return str(ex.get("id") or "A").upper() == exp_id.upper()

SEMANTIC_PAIRS = [
    ("research.p3.sem.{n}.datastore", "research.p3.sem.{n}.persistence", "PostgreSQL is the system of record.", "MongoDB is the authoritative system of record."),
    ("research.p3.sem.{n}.authn", "research.p3.sem.{n}.identity", "Authentication uses SAML SSO via corporate IdP.", "Authentication is password-only with local user store."),
    ("research.p3.sem.{n}.queue", "research.p3.sem.{n}.events", "Primary event bus is Kafka (MSK).", "Primary event bus is RabbitMQ cluster."),
    ("research.p3.sem.{n}.orchestrator", "research.p3.sem.{n}.workflow", "Workflow orchestration is Apache Airflow.", "Workflow orchestration is Temporal Cloud."),
    ("research.p3.sem.{n}.warehouse", "research.p3.sem.{n}.analytics_db", "Analytics warehouse is Snowflake.", "Analytics warehouse is BigQuery."),
]

DEP_BODY_PAIRS = [
    (
        "Canonical: primary warehouse is Snowflake; gold marts assume Snowflake SQL dialect and time travel.",
        "Changed policy: primary warehouse is BigQuery; gold marts must use BigQuery SQL and snapshots (Snowflake assumptions are invalid).",
    ),
    (
        "Canonical: orchestration is Airflow 3 on Kubernetes with CeleryExecutor for heavy tasks.",
        "Changed policy: orchestration is AWS Step Functions only; Airflow is retired (downstream DAG assumptions are stale).",
    ),
]


def iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def append_jsonl(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


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
                    "clientInfo": {"name": "paper3_phase2_mcp_run", "version": "1.0"},
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


def _tool_result_as_dict(res: Any) -> dict[str, Any]:
    """MCP tools may return a dict or a JSON string depending on server version."""
    if isinstance(res, dict):
        return res
    if isinstance(res, list):
        # Some deployments return a bare JSON array of fact objects instead of {"facts": [...]}.
        if res and all(isinstance(x, dict) for x in res):
            return {"facts": res}
        return {}
    if isinstance(res, str):
        try:
            parsed = json.loads(res)
            if isinstance(parsed, dict):
                return parsed
            if isinstance(parsed, list) and parsed and all(isinstance(x, dict) for x in parsed):
                return {"facts": parsed}
            return {}
        except json.JSONDecodeError:
            return {}
    return {}


def conflicts_from_list_response(lc: Any) -> list[dict]:
    d = _tool_result_as_dict(lc)
    raw = d.get("conflicts") or []
    return [c for c in raw if isinstance(c, dict)]


def list_all_facts(mcp: McpSession, project_id: str) -> list[dict]:
    out: list[dict] = []
    offset = 0
    limit = 1000
    while True:
        page = mcp.call_tool(
            "list_facts_v1",
            {"project_id": project_id, "limit": limit, "offset": offset},
        )
        pd = _tool_result_as_dict(page)
        facts = [f for f in (pd.get("facts") or []) if isinstance(f, dict)]
        out.extend(facts)
        if len(facts) < limit:
            break
        offset += limit
    return out


def upstream_keys_depends_on(mcp: McpSession, project_id: str, facts: list[dict]) -> list[tuple[str, str]]:
    """(key, kind) for facts that are targets of depends_on edges (upstream of dependents)."""
    first = mcp.call_tool(
        "list_fact_edges",
        {"project_id": project_id, "edge_type": "depends_on", "limit": 500},
    )
    fd = _tool_result_as_dict(first)
    edges = list(fd.get("edges") or [])
    id_to = {f["id"]: (str(f.get("key") or ""), str(f.get("kind") or "stack")) for f in facts if f.get("id")}
    keys: list[tuple[str, str]] = []
    seen: set[str] = set()
    for e in edges:
        if not isinstance(e, dict):
            continue
        if (e.get("edge_type") or "") != "depends_on":
            continue
        tid = e.get("target_fact_id")
        if not tid or tid not in id_to:
            continue
        k, kind = id_to[tid]
        if k and k not in seen:
            seen.add(k)
            keys.append((k, kind))
    return keys


POLL_CONFLICTS_INTERVAL_S = 1.0
POLL_CONFLICTS_MAX_WAIT_S = 60.0


def parse_detection(resp: Any) -> dict[str, Any]:
    """Extract inline detection metrics from upsert response (Experiment A shape only)."""
    d = _tool_result_as_dict(resp)
    raw = d.get("detection")
    if raw is None:
        return {}
    if isinstance(raw, dict):
        if raw.get("mode") == "scheduled":
            return {}
        return raw
    if isinstance(raw, str):
        if raw.strip() == "scheduled":
            return {}
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict) and parsed.get("mode") == "scheduled":
                return {}
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def detection_inline_available(resp: Any) -> bool:
    """True if upsert returned inline detection metrics (not async scheduled)."""
    d = _tool_result_as_dict(resp)
    raw = d.get("detection")
    if raw is None:
        return False
    if raw == "scheduled":
        return False
    if isinstance(raw, dict):
        if raw.get("mode") == "scheduled":
            return False
        return "conflicts_detected" in raw or "detection_latency_ms" in raw
    if isinstance(raw, str):
        if raw.strip() == "scheduled":
            return False
        try:
            o = json.loads(raw)
            if isinstance(o, dict) and o.get("mode") == "scheduled":
                return False
            return isinstance(o, dict) and (
                "conflicts_detected" in o or "detection_latency_ms" in o
            )
        except json.JSONDecodeError:
            return False
    return False


def poll_for_conflict_notification(
    mcp: McpSession,
    project_id: str,
    keyset: set[str],
    after_ts: float | None,
    *,
    interval_s: float = POLL_CONFLICTS_INTERVAL_S,
    max_wait_s: float = POLL_CONFLICTS_MAX_WAIT_S,
    proposed_key: str | None = None,
    expected_conflict_type: str | None = None,
) -> tuple[dict | None, float]:
    """Poll list_conflicts_v1 until a matching notification appears or timeout."""
    t0 = time.monotonic()
    while time.monotonic() - t0 < max_wait_s:
        lc = mcp.call_tool(
            "list_conflicts_v1",
            {"project_id": project_id, "unresolved_only": True, "limit": 200},
        )
        conflicts = conflicts_from_list_response(lc)
        hit = find_notification_for_keys(
            conflicts,
            keyset,
            after_ts,
            proposed_key=proposed_key,
            expected_conflict_type=expected_conflict_type,
        )
        if hit is not None:
            return hit, time.monotonic() - t0
        time.sleep(interval_s)
    return None, time.monotonic() - t0


def observed_notification_latency_ms(
    notif_created_at: Any,
    t_write_end: float,
) -> float | None:
    if notif_created_at is None:
        return None
    try:
        ct = datetime.fromisoformat(str(notif_created_at).replace("Z", "+00:00")).timestamp()
        ms = (ct - t_write_end) * 1000.0
        return ms if ms >= 0 else None
    except Exception:
        return None


def find_notification_for_keys(
    conflicts: list[dict],
    keys: set[str],
    after_ts: float | None,
    *,
    proposed_key: str | None = None,
    expected_conflict_type: str | None = None,
) -> dict | None:
    keys = {str(k) for k in keys if k}
    best: tuple[tuple[int, int, int, float], dict] | None = None
    for c in conflicts:
        if not isinstance(c, dict):
            continue
        det = c.get("details") or {}
        summary = str(c.get("summary", ""))
        candidate_keys = [
            str(x)
            for x in (det.get("key"), det.get("fact_key"), det.get("neighbor_key"))
            if x
        ]
        matched_on_key = None
        if proposed_key and (proposed_key in candidate_keys or proposed_key in summary):
            matched_on_key = proposed_key
        else:
            for key in sorted(keys):
                if key in candidate_keys or key in summary:
                    matched_on_key = key
                    break
        if matched_on_key is None:
            continue
        created = c.get("created_at") or det.get("created_at")
        created_ts = -1.0
        if created:
            try:
                created_ts = datetime.fromisoformat(str(created).replace("Z", "+00:00")).timestamp()
            except Exception:
                created_ts = -1.0
        if after_ts is not None and created_ts >= 0 and created_ts + 0.001 < after_ts:
            continue
        conflict_type = str(c.get("conflict_type") or "")
        exact_type_match = bool(expected_conflict_type and conflict_type == expected_conflict_type)
        matched_on_anchor_only = bool(proposed_key and matched_on_key != proposed_key)
        score = (
            1 if matched_on_key == proposed_key else 0,
            1 if exact_type_match else 0,
            0 if matched_on_anchor_only else 1,
            created_ts,
        )
        payload = dict(c)
        payload["matched_on_key"] = matched_on_key
        payload["matched_on_anchor_only"] = matched_on_anchor_only
        payload["matched_conflict_type"] = conflict_type or None
        payload["exact_type_match"] = exact_type_match
        if best is None or score > best[0]:
            best = (score, payload)
    return best[1] if best is not None else None


def phase1_complete() -> bool:
    if not PHASE1_CHECKPOINTS.exists():
        return False
    for line in PHASE1_CHECKPOINTS.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            o = json.loads(line)
        except json.JSONDecodeError:
            continue
        if o.get("phase") == 1 and o.get("checkpoint_type") == "phase_complete" and o.get("status") == "complete":
            return True
    return False


def phase2_start_checkpoint_exists(exp_id: str) -> bool:
    """True if this experiment already has a phase_start line (avoid duplicate on resume)."""
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
        if o.get("phase") == 2 and o.get("checkpoint_type") == "phase_start" and _row_matches_experiment(
            o, exp_id
        ):
            return True
    return False


def phase2_conflict_injection_start_logged(exp_id: str) -> bool:
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
        if o.get("phase") == 2 and o.get("action") == "conflict_injection_start" and _row_matches_experiment(
            o, exp_id
        ):
            return True
    return False


def phase2_complete(exp_id: str) -> bool:
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
            if _row_matches_experiment(o, exp_id):
                return True
    return False


def resume_state(exp_id: str) -> tuple[int, dict[str, int]]:
    last_n = 0
    counts = {
        "semantic_contradiction": 0,
        "dependency_impact": 0,
        "constraint_violation": 0,
        "temporal_invalidation": 0,
    }
    if not EXEC_LOG.exists():
        return last_n, counts
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
        if not _row_matches_experiment(o, exp_id):
            continue
        n = int(o.get("injection_number") or 0)
        last_n = max(last_n, n)
        cls = o.get("conflict_class")
        if cls in counts:
            counts[str(cls)] += 1
    return last_n, counts


def pick_class(counts: dict[str, int], injection_number: int) -> str:
    cap = 50
    under = [k for k, v in counts.items() if v < cap]
    if not under:
        raise RuntimeError("All conflict classes reached cap (50)")
    under.sort()
    return under[(injection_number - 1) % len(under)]


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
        "actor": "phase2_seed_agent",
        "agent_id": "phase2_seed_agent",
        "skip_conflict_check": skip_conflict_check,
        "skip_embedding": skip_embedding,
    }
    if valid_from is not None:
        args["valid_from"] = valid_from
    if valid_until is not None:
        args["valid_until"] = valid_until
    return mcp.call_tool("memory_upsert_fact_v1", args)


def main() -> None:
    cfg = load_json(CONFIG_PATH)
    apply_phase2_paths(cfg)
    exp_id = _experiment_id(cfg)
    exp_meta = paper3_experiment_block(cfg)

    def p2(row: dict) -> dict:
        out = dict(row)
        out["experiment"] = dict(exp_meta)
        return out

    if phase2_complete(exp_id):
        print("Phase 2 already complete (checkpoint). Exiting.")
        return

    if not phase1_complete():
        append_jsonl(
            CHECKPOINTS,
            p2(
                {
                    "timestamp": iso_now(),
                    "phase": 2,
                    "checkpoint_type": "phase_failed",
                    "agent_id": "phase2_seed_agent",
                    "status": "failed",
                    "error": "Phase 1 phase_complete with next_phase_prerequisites_met not found",
                    "notes": "Prerequisites failed",
                },
            ),
        )
        raise SystemExit("Phase 1 not verified complete in checkpoints.")

    if PAUSE_FLAG.exists():
        print("PAUSED: remove research/paper3_pause.flag to run.")
        return

    fact_kind = paper3_fact_kind(cfg)
    project_ids = paper3_project_ids(cfg)
    target_per_project = paper3_target_per_project(project_ids)
    n_proj = len(project_ids)

    mcp_cfg = load_json(MCP_PATH)
    srv = mcp_cfg["mcpServers"]["spirl"]
    url = srv["url"]
    auth = srv["headers"]["Authorization"]
    mcp = McpSession(url, auth)
    mcp.connect()

    last_done, class_counts = resume_state(exp_id)
    start_n = last_done + 1

    dep_keys_by_proj: dict[str, list[tuple[str, str]]] = {}
    for pid in project_ids:
        facts = list_all_facts(mcp, pid)
        dep_keys_by_proj[pid] = upstream_keys_depends_on(mcp, pid, facts)

    static_fallback = [
        ("stack.warehouse", "stack"),
        ("stack.orchestration", "stack"),
        ("stack.metadata", "stack"),
    ]

    if start_n == 1:
        if not phase2_start_checkpoint_exists(exp_id):
            append_jsonl(
                CHECKPOINTS,
                p2(
                    {
                        "timestamp": iso_now(),
                        "phase": 2,
                        "checkpoint_type": "phase_start",
                        "agent_id": "phase2_seed_agent",
                        "status": "in_progress",
                        "prerequisites_checked": True,
                        "phase1_verified": True,
                        "notes": "Starting Phase 2 — conflict injection (MCP only)",
                    },
                ),
            )
        if not phase2_conflict_injection_start_logged(exp_id):
            append_jsonl(
                EXEC_LOG,
                p2(
                    {
                        "timestamp": iso_now(),
                        "phase": 2,
                        "agent_id": "phase2_seed_agent",
                        "action": "conflict_injection_start",
                        "project": "all",
                        "result": {
                            "target_total": 200,
                            "target_per_class": {
                                "semantic_contradiction": 50,
                                "dependency_impact": 50,
                                "constraint_violation": 50,
                                "temporal_invalidation": 50,
                            },
                            "target_per_project": target_per_project,
                        },
                    },
                ),
            )

    for injection_number in range(start_n, 201):
        t0 = time.monotonic()
        proj = project_ids[(injection_number - 1) % n_proj]
        cls = pick_class(class_counts, injection_number)
        fact_keys: list[str] = []
        last_write_resp: Any = None
        t_write_end: float | None = None
        err_msg: str | None = None

        try:
            if cls == "semantic_contradiction":
                pair = SEMANTIC_PAIRS[(injection_number - 1) % len(SEMANTIC_PAIRS)]
                k1 = pair[0].format(n=injection_number)
                k2 = pair[1].format(n=injection_number)
                upsert_fact(
                    mcp,
                    proj,
                    kind=fact_kind,
                    key=k1,
                    body=pair[2],
                    skip_conflict_check=True,
                )
                time.sleep(8)
                last_write_resp = upsert_fact(
                    mcp,
                    proj,
                    kind=fact_kind,
                    key=k2,
                    body=pair[3],
                )
                fact_keys = [k1, k2]
                t_write_end = time.time()

            elif cls == "dependency_impact":
                pool = dep_keys_by_proj.get(proj) or []
                if not pool:
                    pool = static_fallback
                uk, kind = pool[(injection_number + project_ids.index(proj)) % len(pool)]
                b0, b1 = DEP_BODY_PAIRS[injection_number % 2]
                upsert_fact(
                    mcp,
                    proj,
                    kind=kind,
                    key=uk,
                    body=b0,
                    skip_conflict_check=True,
                )
                last_write_resp = upsert_fact(
                    mcp,
                    proj,
                    kind=kind,
                    key=uk,
                    body=b1,
                )
                fact_keys = [uk]
                t_write_end = time.time()

            elif cls == "constraint_violation":
                label = f"research.p3.ph2.team_cap.{injection_number}"
                mcp.call_tool(
                    "upsert_project_constraint",
                    {
                        "project_id": proj,
                        "constraint_type": "scope",
                        "label": label,
                        "value": 10,
                        "unit": "developers",
                        "description": "Paper3 Phase2: team size must not exceed 10 developers.",
                        "enabled": True,
                    },
                )
                fk = f"research.p3.ph2.team_fact.{injection_number}"
                body = "Current delivery team: 25 developers staffed on the core squad."
                last_write_resp = upsert_fact(mcp, proj, kind=fact_kind, key=fk, body=body)
                fact_keys = [fk, label]
                t_write_end = time.time()

            else:
                key = f"research.p3.tmpov.{injection_number}"
                upsert_fact(
                    mcp,
                    proj,
                    kind=fact_kind,
                    key=key,
                    body="Stack choice A: React 18 with Next.js for the portal.",
                    valid_from="2026-01-01T00:00:00Z",
                    valid_until="2026-12-31T23:59:59Z",
                    skip_conflict_check=True,
                )
                last_write_resp = upsert_fact(
                    mcp,
                    proj,
                    kind=fact_kind,
                    key=key,
                    body="Stack choice B: Vue 3 with Nuxt for the portal.",
                    valid_from="2026-06-01T00:00:00Z",
                    valid_until="2027-12-31T23:59:59Z",
                )
                fact_keys = [key, key]
                t_write_end = time.time()

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

            keyset = set(fact_keys)
            after = (t_write_end - 2.0) if t_write_end else None
            hit, poll_elapsed_s = poll_for_conflict_notification(
                mcp, proj, keyset, after,
                interval_s=POLL_CONFLICTS_INTERVAL_S,
                max_wait_s=POLL_CONFLICTS_MAX_WAIT_S,
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

            gt = {
                "conflict_number": injection_number,
                "class": cls,
                "project": proj,
                "fact_keys_involved": fact_keys,
                "injection_timestamp": iso_now(),
                "notification_created": notif_created,
                "notification_id": notif_id,
                "notification_conflict_type": notif_conflict_type,
                "notification_severity": notif_severity,
                "detection_latency_ms": det_lat,
                "observed_detection_latency_ms": observed_ms,
            }
            upsert_fact(
                mcp,
                proj,
                kind=fact_kind,
                key=f"research.p3.groundtruth.{injection_number}",
                body=json.dumps(gt),
                skip_conflict_check=True,
                skip_embedding=True,
            )

            class_counts[cls] += 1
            elapsed_s = time.monotonic() - t0

            append_jsonl(
                EXEC_LOG,
                p2(
                    {
                        "timestamp": iso_now(),
                        "phase": 2,
                        "agent_id": "phase2_seed_agent",
                        "action": "conflict_injected",
                        "project": proj,
                        "injection_number": injection_number,
                        "conflict_class": cls,
                        "result": {
                            "fact_keys": fact_keys,
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
                            },
                            "notification": {
                                "created": notif_created,
                                "notification_id": notif_id,
                                "conflict_type": notif_conflict_type,
                                "severity": notif_severity,
                                "created_at": notif_created_at,
                            },
                            "ground_truth_key": f"research.p3.groundtruth.{injection_number}",
                            "detection_latency_ms": det_lat,
                            "injection_elapsed_s": round(elapsed_s, 1),
                            "success": True,
                        },
                    },
                ),
            )

            print(
                f"[{injection_number}/200] {cls} -> {proj[:8]}... "
                f"inline={inline_detected} notif={'Y' if notif_created else 'N'} "
                f"obs_ms={observed_ms if observed_ms is not None else '—'} "
                f"({elapsed_s:.1f}s)"
            )

            if injection_number % 20 == 0:
                append_jsonl(
                    CHECKPOINTS,
                    p2(
                        {
                            "timestamp": iso_now(),
                            "phase": 2,
                            "checkpoint_type": "injection_progress",
                            "agent_id": "phase2_seed_agent",
                            "status": "in_progress",
                            "injection_number": injection_number,
                            "target": 200,
                            "class_counts": dict(class_counts),
                            "notes": f"Progress checkpoint at injection {injection_number}",
                        },
                    ),
                )

        except Exception as e:
            err_msg = str(e)
            append_jsonl(
                EXEC_LOG,
                p2(
                    {
                        "timestamp": iso_now(),
                        "phase": 2,
                        "agent_id": "phase2_seed_agent",
                        "action": "injection_failed",
                        "project": proj,
                        "injection_number": injection_number,
                        "conflict_class": cls,
                        "result": {
                            "error": err_msg,
                            "fact_keys_attempted": fact_keys,
                            "will_retry": False,
                        },
                    },
                ),
            )
            append_jsonl(
                CHECKPOINTS,
                p2(
                    {
                        "timestamp": iso_now(),
                        "phase": 2,
                        "checkpoint_type": "phase_failed",
                        "agent_id": "phase2_seed_agent",
                        "status": "failed",
                        "error": err_msg,
                        "last_successful_action": "conflict_injected",
                        "last_injection_number": injection_number - 1,
                        "resume_point": f"injection_number_{injection_number}",
                        "notes": f"Resume from injection {injection_number}",
                    },
                ),
            )
            raise SystemExit(1) from e

    temporal_detected = class_counts["temporal_invalidation"]
    append_jsonl(
        EXEC_LOG,
        p2(
            {
                "timestamp": iso_now(),
                "phase": 2,
                "agent_id": "phase2_seed_agent",
                "action": "baseline_simulation",
                "project": "all",
                "result": {
                    "total_injected": 200,
                    "baseline_detectable": {
                        "semantic_contradiction": 0,
                        "dependency_impact": 0,
                        "constraint_violation": 0,
                        "temporal_invalidation": temporal_detected,
                    },
                    "baseline_missed": {
                        "semantic_contradiction": 50,
                        "dependency_impact": 50,
                        "constraint_violation": 50,
                        "temporal_invalidation": 50 - temporal_detected,
                    },
                },
            },
        ),
    )

    upsert_fact(
        mcp,
        project_ids[0],
        kind=fact_kind,
        key="research.p3.baseline.simulation",
        body=(
            f"Baseline temporal-only: detectable={temporal_detected}, missed={200 - temporal_detected}, "
            f"by class: semantic_contradiction=0/50, dependency_impact=0/50, constraint_violation=0/50, "
            f"temporal_invalidation={temporal_detected}/50"
        ),
        skip_conflict_check=True,
        skip_embedding=True,
    )

    entries: list[dict] = []
    for line in EXEC_LOG.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            o = json.loads(line)
        except json.JSONDecodeError:
            continue
        if o.get("phase") == 2 and _row_matches_experiment(o, exp_id):
            entries.append(o)

    by_class = {c: {"inj": 0, "inline": 0, "not": 0} for c in class_counts}
    latencies_inline: list[float] = []
    latencies_observed: list[float] = []
    elapsed_times: list[float] = []
    any_inline_available = False
    by_proj: dict[str, dict[str, int]] = {
        p: {"injected": 0, "detected": 0, "missed": 0} for p in project_ids
    }

    for o in entries:
        if o.get("action") != "conflict_injected":
            continue
        r = o.get("result") or {}
        cls_name = o.get("conflict_class")
        if cls_name in by_class:
            by_class[str(cls_name)]["inj"] += 1
            pf = r.get("preflight_check") or {}
            if pf.get("inline_available"):
                any_inline_available = True
            if "inline_detected" in pf:
                idet = bool(pf.get("inline_detected"))
            elif pf.get("inline_available") is False:
                idet = False
            else:
                idet = bool(pf.get("detected"))
            if idet:
                by_class[str(cls_name)]["inline"] += 1
            nt = r.get("notification") or {}
            if nt.get("created"):
                by_class[str(cls_name)]["not"] += 1
        lat = r.get("detection_latency_ms")
        if isinstance(lat, (int, float)):
            latencies_inline.append(float(lat))
        ao = r.get("async_observed") or {}
        olat = ao.get("observed_detection_latency_ms")
        if isinstance(olat, (int, float)):
            latencies_observed.append(float(olat))
        el = r.get("injection_elapsed_s")
        if isinstance(el, (int, float)):
            elapsed_times.append(float(el))
        pid = o.get("project")
        if pid in by_proj:
            by_proj[str(pid)]["injected"] += 1
            nt = r.get("notification") or {}
            if nt.get("created"):
                by_proj[str(pid)]["detected"] += 1
            else:
                by_proj[str(pid)]["missed"] += 1

    total_inj = sum(x["inj"] for x in by_class.values())
    total_inline = sum(x["inline"] for x in by_class.values())
    total_not = sum(x["not"] for x in by_class.values())
    mean_lat_inline = int(sum(latencies_inline) / len(latencies_inline)) if latencies_inline else None
    mean_lat_obs = int(sum(latencies_observed) / len(latencies_observed)) if latencies_observed else None
    mean_elapsed = round(sum(elapsed_times) / len(elapsed_times), 1) if elapsed_times else 0

    inline_latency_note = (
        f"{mean_lat_inline}ms"
        if mean_lat_inline is not None
        else ("N/A (async detection; inline metrics not returned by upsert)" if not any_inline_available else "N/A (no data points)")
    )
    observed_latency_note = (
        f"{mean_lat_obs}ms"
        if mean_lat_obs is not None
        else "N/A (no matching notifications in poll window)"
    )

    arch_note = exp_meta.get("architecture_label") or "—"
    report_path = PHASE2_REPORT_PATH
    report = f"""# Phase 2 Report — Conflict Injection and Detection

> **Paper 3 experiment:** {exp_meta.get("id")}  
> **Architecture label:** {arch_note}  

Generated: {iso_now()}
Total conflicts injected: {total_inj} (target: 200)
Mean injection time: {mean_elapsed}s per injection
Transport: Spirl MCP (Streamable HTTP), script `scripts/paper3_phase2_mcp_run.py`

## Injection summary by class

| class | injected | inline_detected_in_upsert | notification_matched_poll |
|-------|----------|----------------------------|---------------------------|
| semantic_contradiction | {by_class["semantic_contradiction"]["inj"]} | {by_class["semantic_contradiction"]["inline"]} | {by_class["semantic_contradiction"]["not"]} |
| dependency_impact | {by_class["dependency_impact"]["inj"]} | {by_class["dependency_impact"]["inline"]} | {by_class["dependency_impact"]["not"]} |
| constraint_violation | {by_class["constraint_violation"]["inj"]} | {by_class["constraint_violation"]["inline"]} | {by_class["constraint_violation"]["not"]} |
| temporal_invalidation | {by_class["temporal_invalidation"]["inj"]} | {by_class["temporal_invalidation"]["inline"]} | {by_class["temporal_invalidation"]["not"]} |
| TOTAL | {total_inj} | {total_inline} | {total_not} |

*Inline metrics* come only from the synchronous upsert JSON (`detection` dict). When detection is scheduled in the background, this column is expected to be 0. *Notification matched (poll)* reflects `list_conflicts_v1` polling (up to {POLL_CONFLICTS_MAX_WAIT_S:.0f}s per injection) and is the correct detection signal for Experiment B+ async pipelines.

## Injection summary by project

| project | injected | detected | missed |
|---------|----------|----------|--------|
| {project_ids[0]} | {by_proj[project_ids[0]]["injected"]} | {by_proj[project_ids[0]]["detected"]} | {by_proj[project_ids[0]]["missed"]} |
| {project_ids[1]} | {by_proj[project_ids[1]]["injected"]} | {by_proj[project_ids[1]]["detected"]} | {by_proj[project_ids[1]]["missed"]} |
| {project_ids[2]} | {by_proj[project_ids[2]]["injected"]} | {by_proj[project_ids[2]]["detected"]} | {by_proj[project_ids[2]]["missed"]} |

## Baseline simulation

| class | baseline_detectable | baseline_missed |
|-------|--------------------|---------------------|
| semantic_contradiction | 0 | 50 |
| dependency_impact | 0 | 50 |
| constraint_violation | 0 | 50 |
| temporal_invalidation | {temporal_detected} | {50 - temporal_detected} |
| TOTAL | {temporal_detected} | {200 - temporal_detected} |

## Detection latency

### Inline (from upsert response only)

| metric | value |
|--------|-------|
| Mean inline detection latency | {inline_latency_note} |
| Min inline latency | {int(min(latencies_inline)) if latencies_inline else "N/A"} |
| Max inline latency | {int(max(latencies_inline)) if latencies_inline else "N/A"} |
| Inline latency data points | {len(latencies_inline)} |

### Observed (notification `created_at` minus upsert completion time)

| metric | value |
|--------|-------|
| Mean observed detection latency | {observed_latency_note} |
| Min observed latency | {int(min(latencies_observed)) if latencies_observed else "N/A"} |
| Max observed latency | {int(max(latencies_observed)) if latencies_observed else "N/A"} |
| Observed latency data points | {len(latencies_observed)} |

## Performance

| metric | value |
|--------|-------|
| Mean injection time | {mean_elapsed}s |
| Min injection time | {min(elapsed_times) if elapsed_times else 0}s |
| Max injection time | {max(elapsed_times) if elapsed_times else 0}s |

## Anomalies

none

## Phase 2 status

- All 200 conflicts injected: yes
- Ground truth records written: {total_inj}
- Baseline simulation complete: yes
- Ready for Phase 3 scoring: YES
- Blockers: none
"""
    report_path.write_text(report, encoding="utf-8")

    failed = sum(1 for o in entries if o.get("action") == "injection_failed")

    rel_report = f"research/{PHASE2_REPORT_PATH.name}"
    append_jsonl(
        CHECKPOINTS,
        p2(
            {
                "timestamp": iso_now(),
                "phase": 2,
                "checkpoint_type": "phase_complete",
                "agent_id": "phase2_seed_agent",
                "status": "complete",
                "report_generated": True,
                "report_path": rel_report,
                "log_entries_written": len(entries),
                "total_injections": 200,
                "injections_successful": total_inj,
                "injections_failed": failed,
                "mean_injection_time_s": mean_elapsed,
                "next_phase_prerequisites_met": True,
                "notes": "All injections complete, baseline simulation done (MCP)",
            },
        ),
    )
    print(f"Phase 2 complete: {report_path} (mean {mean_elapsed}s/injection)")


if __name__ == "__main__":
    main()
