#!/usr/bin/env python3
"""
Create a Spirl project (optional) and import real-data-lab SKF via MCP tools/call import_skf.

Reads bearer token the same way as paper3_phase1_mcp_run: .cursor/mcp.json -> mcpServers.spirl.headers.Authorization.

Usage:
  python import_real_data_lab_skf_mcp.py [--skf PATH] [--project-id UUID] [--no-create]

If --project-id is omitted, POST /v1/projects with name from SKF, then import into returned id.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

try:
    import requests
except ImportError as e:  # pragma: no cover
    raise SystemExit("pip install requests") from e

from repair_real_data_lab_skf import (  # noqa: E402
    DEFAULT_SKF,
    facts_for_import_skf,
    repair_skf_text,
)

ROOT = _SCRIPTS.parent.parent
MCP_JSON = ROOT / ".cursor" / "mcp.json"
SPIRL_CONFIG = ROOT / ".spirl" / "config.json"


def load_bearer() -> str:
    data = json.loads(MCP_JSON.read_text(encoding="utf-8"))
    auth = (data.get("mcpServers") or {}).get("spirl", {}).get("headers", {}).get("Authorization", "")
    if not auth or not str(auth).lower().startswith("bearer "):
        raise SystemExit(f"Missing Bearer in {MCP_JSON}")
    return str(auth)


def load_skf_doc(path: Path) -> dict[str, Any]:
    raw = path.read_text(encoding="utf-8")
    repaired = repair_skf_text(raw)
    return json.loads(repaired)


def mcp_call(url: str, token: str, session_id: str | None, method: str, params: dict) -> dict:
    mid = 1
    payload = {"jsonrpc": "2.0", "id": mid, "method": method, "params": params}
    hdrs = {
        "Authorization": token,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if session_id:
        hdrs["Mcp-Session-Id"] = session_id
    r = requests.post(url.rstrip("/"), headers=hdrs, json=payload, timeout=600)
    r.raise_for_status()
    body = r.json()
    if body.get("error"):
        raise RuntimeError(body["error"])
    return body.get("result", body)


def mcp_initialize(url: str, token: str) -> str:
    r = requests.post(
        url.rstrip("/"),
        headers={
            "Authorization": token,
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "import_real_data_lab_skf_mcp", "version": "1.0"},
            },
        },
        timeout=120,
    )
    r.raise_for_status()
    sid = r.headers.get("mcp-session-id") or r.headers.get("Mcp-Session-Id")
    if not sid:
        raise RuntimeError("No Mcp-Session-Id from initialize")
    return sid


def mcp_import_skf(url: str, token: str, arguments: dict) -> Any:
    sid = mcp_initialize(url, token)
    res = mcp_call(
        url,
        token,
        sid,
        "tools/call",
        {"name": "import_skf", "arguments": arguments},
    )
    if not res or "content" not in res:
        return res
    for p in res.get("content") or []:
        if isinstance(p, dict) and p.get("type") == "text":
            txt = p.get("text") or ""
            try:
                return json.loads(txt)
            except json.JSONDecodeError:
                return txt
    return res


def create_project(api_base: str, token: str, name: str) -> str:
    r = requests.post(
        f"{api_base.rstrip('/')}/v1/projects",
        headers={"Authorization": token, "Content-Type": "application/json"},
        json={"name": name},
        timeout=60,
    )
    r.raise_for_status()
    out = r.json()
    pid = out.get("id") or out.get("project_id")
    if not pid:
        raise RuntimeError(f"Unexpected create project response: {out}")
    return str(pid)


def update_spirl_config(project_id: str, name_key: str = "real_data_lab_project_core_platform") -> None:
    if not SPIRL_CONFIG.is_file():
        return
    cfg = json.loads(SPIRL_CONFIG.read_text(encoding="utf-8"))
    projects = cfg.get("projects")
    if isinstance(projects, dict):
        projects[name_key] = project_id
        cfg["projects"] = projects
    cfg["real_data_lab_project_id"] = project_id
    SPIRL_CONFIG.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skf", type=Path, default=DEFAULT_SKF)
    ap.add_argument("--project-id", type=str, default="", help="Existing Spirl project UUID")
    ap.add_argument("--no-create", action="store_true", help="Require --project-id; do not POST /v1/projects")
    ap.add_argument("--mcp-url", default="http://localhost:8000/mcp")
    ap.add_argument("--api-base", default="http://localhost:8000")
    ap.add_argument("--write-config", action="store_true", help=f"Store id in {SPIRL_CONFIG}")
    args = ap.parse_args()

    token = load_bearer()
    doc = load_skf_doc(args.skf)
    proj = doc.get("project") or {}
    facts = facts_for_import_skf(doc)
    if not facts:
        print("No facts to import.", file=sys.stderr)
        return 1

    project_id = (args.project_id or "").strip()
    if not project_id:
        if args.no_create:
            print("Provide --project-id or omit --no-create.", file=sys.stderr)
            return 1
        project_id = create_project(args.api_base, token, str(proj.get("name") or "Project Core Platform"))
        print("Created project:", project_id)

    payload = {
        "project_id": project_id,
        "skf_version": str(doc.get("skf_version") or "1.2"),
        "project": proj,
        "facts": facts,
        "source": doc.get("source") or {},
    }

    out = mcp_import_skf(args.mcp_url, token, payload)
    print(json.dumps(out, ensure_ascii=False, indent=2) if isinstance(out, (dict, list)) else out)

    if args.write_config:
        update_spirl_config(project_id)
        print(f"Updated {SPIRL_CONFIG}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
