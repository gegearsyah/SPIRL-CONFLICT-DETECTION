#!/usr/bin/env python3
"""
Build 40+ agent-ready prompts from an SKF v1.2 JSON file.

Each line targets one Paper-3-style conflict class where possible:
  semantic_contradiction, dependency_impact, constraint_violation, temporal_invalidation

Usage:
  python skf_conflict_prompt_generator.py --skf ../research/paper3_seed_api_service.skf.json \\
      --out ../research/conflict_prompts.live.jsonl --min-prompts 45

Optional: --project-id UUID for echo into each row (agents paste into MCP calls).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


def load_skf(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def slug(s: str, max_len: int = 48) -> str:
    x = re.sub(r"[^a-zA-Z0-9._-]+", "_", s.strip())[:max_len].strip("_")
    return x or "fact"


def kind_from_category(cat: str) -> str:
    m = {
        "stack": "decision",
        "decision": "decision",
        "feature": "decision",
        "constraint": "constraint",
        "api_endpoint": "decision",
        "deployment": "decision",
        "behavioral_contract": "constraint",
        "data_flow": "decision",
        "module_cluster": "decision",
        "migration": "decision",
        "test": "decision",
        "monitoring": "decision",
        "deprecated": "decision",
        "other": "decision",
    }
    return m.get(cat, "decision")


def opposite_stub(value: str) -> str:
    """Cheap lexical flip for deterministic injection tests (not semantically perfect)."""
    t = value
    pairs = [
        (r"\bPostgreSQL\b", "MySQL"),
        (r"\bMySQL\b", "PostgreSQL"),
        (r"\bMongoDB\b", "PostgreSQL"),
        (r"\bRedis\b", "Memcached"),
        (r"\bRabbitMQ\b", "Apache Kafka"),
        (r"\bKafka\b", "RabbitMQ"),
        (r"\bJWT\b", "opaque session cookies"),
        (r"\bsession cookies\b", "JWT bearer tokens"),
        (r"\bREST\b", "GraphQL"),
        (r"\bGraphQL\b", "REST"),
        (r"\bReact\b", "Vue 3"),
        (r"\bVue\b", "React 18"),
        (r"\bKubernetes\b", "Docker Swarm"),
        (r"\bDocker Swarm\b", "Kubernetes"),
        (r"\bNATS\b", "Redis Streams"),
        (r"\bHTTPS\b", "unencrypted HTTP on the internal mesh"),
    ]
    out = t
    for pat, rep in pairs:
        if re.search(pat, out, re.I):
            return re.sub(pat, rep, out, count=1, flags=re.I)
    if len(out) > 200:
        return "CONTRADICTION (injection): " + out[:180] + " … [reversed policy: implementation must not rely on the above; use an incompatible alternative]."
    return "CONTRADICTION (injection): negate prior claim — " + out


def build_prompts(
    data: dict[str, Any],
    project_id: str,
    min_prompts: int,
) -> list[dict[str, Any]]:
    facts: list[dict[str, Any]] = list(data.get("facts") or [])
    rels: list[dict[str, Any]] = list(data.get("relationships") or [])
    rules: list[dict[str, Any]] = list(data.get("rules") or [])
    project_name = (data.get("project") or {}).get("name") or "unknown_project"

    rows: list[dict[str, Any]] = []
    pid_note = f' Spirl project_id: `{project_id}`.' if project_id else ""

    # --- Semantic: one per fact (different key, contradictory body) ---
    for i, f in enumerate(facts):
        k = f.get("key") or f"fact.{i}"
        val = str(f.get("value") or "")
        cat = str(f.get("category") or "other")
        new_key = f"live_inject.semantic.{slug(k)}.{i:03d}"
        new_body = opposite_stub(val)
        rows.append(
            {
                "prompt_id": f"semantic_{i:03d}",
                "conflict_class": "semantic_contradiction",
                "target_fact_key": k,
                "project_name": project_name,
                "mcp_tool": "memory_upsert_fact_v1",
                "deterministic_upsert": {
                    "kind": kind_from_category(cat),
                    "key": new_key,
                    "body": new_body[:12000],
                    "tier": 1,
                    "tags": ["live_inject", "semantic_contradiction", f"targets:{k}"],
                    "source_type": "synthetic",
                    "actor": "conflict_prompt_agent",
                    "confidence": 0.85,
                },
                "agent_prompt": (
                    f"You are a Spirl MCP agent.{pid_note} Ground fact in graph: key=`{k}` "
                    f"states: {val[:900]}{'…' if len(val) > 900 else ''}\n\n"
                    "Inject ONE new fact using `memory_upsert_fact_v1` with a **different** key that "
                    "asserts an **incompatible** architectural or product truth about the same concern "
                    "(cross-key semantic contradiction). Do not delete the original fact. "
                    f"Suggested key: `{new_key}`. Body must be clearly contradictory to the ground fact."
                ),
            }
        )

    # --- Temporal: same key, overlapping validity (two-step) ---
    for j, f in enumerate(facts[: min(12, len(facts))]):
        k = f.get("key") or f"fact.{j}"
        val = str(f.get("value") or "")[:500]
        rows.append(
            {
                "prompt_id": f"temporal_a_{j:03d}",
                "conflict_class": "temporal_invalidation",
                "target_fact_key": k,
                "project_name": project_name,
                "mcp_tool": "memory_upsert_fact_v1",
                "deterministic_upsert": {
                    "kind": kind_from_category(str(f.get("category") or "decision")),
                    "key": k,
                    "body": val + " [temporal seed A]",
                    "tier": 1,
                    "valid_from": "2026-01-01T00:00:00Z",
                    "valid_until": "2026-12-31T23:59:59Z",
                    "tags": ["live_inject", "temporal_seed_a"],
                    "source_type": "synthetic",
                    "actor": "conflict_prompt_agent",
                    "confidence": 0.9,
                },
                "agent_prompt": (
                    f"{pid_note} Step 1/2 (temporal): Upsert fact with key EXACTLY `{k}` "
                    f"with valid_from=2026-01-01T00:00:00Z, valid_until=2026-12-31T23:59:59Z, "
                    f"body summarizing: {val[:400]}"
                ),
            }
        )
        rows.append(
            {
                "prompt_id": f"temporal_b_{j:03d}",
                "conflict_class": "temporal_invalidation",
                "target_fact_key": k,
                "project_name": project_name,
                "mcp_tool": "memory_upsert_fact_v1",
                "deterministic_upsert": {
                    "kind": kind_from_category(str(f.get("category") or "decision")),
                    "key": k,
                    "body": opposite_stub(str(f.get("value") or ""))[:12000],
                    "tier": 1,
                    "valid_from": "2026-06-01T00:00:00Z",
                    "valid_until": "2027-06-01T00:00:00Z",
                    "tags": ["live_inject", "temporal_seed_b"],
                    "source_type": "synthetic",
                    "actor": "conflict_prompt_agent",
                    "confidence": 0.9,
                },
                "agent_prompt": (
                    f"{pid_note} Step 2/2 (temporal): Upsert SAME key `{k}` with **overlapping** "
                    "valid_from=2026-06-01T00:00:00Z, valid_until=2027-06-01T00:00:00Z and a "
                    "**different** body that contradicts step 1 (triggers temporal overlap)."
                ),
            }
        )

    # --- Dependency: for each depends_on edge, downstream depends on upstream; then mutate upstream ---
    dep_i = 0
    for r in rels:
        if str(r.get("type") or "").lower() != "depends_on":
            continue
        src = r.get("from") or r.get("source")
        tgt = r.get("to") or r.get("target")
        if not src or not tgt:
            continue
        src_f = next((x for x in facts if x.get("key") == src), None)
        tgt_f = next((x for x in facts if x.get("key") == tgt), None)
        if not src_f or not tgt_f:
            continue
        new_upstream_body = opposite_stub(str(tgt_f.get("value") or "upstream fact"))[:12000]
        rows.append(
            {
                "prompt_id": f"dep_setup_{dep_i:03d}",
                "conflict_class": "dependency_impact",
                "target_fact_key": tgt,
                "related_fact_key": src,
                "project_name": project_name,
                "mcp_tool": "create_fact_edge",
                "edge_spec": {
                    "source_fact_key": src,
                    "target_fact_key": tgt,
                    "edge_type": "depends_on",
                },
                "agent_prompt": (
                    f"{pid_note} Dependency setup: Ensure fact `{src}` exists (depends on `{tgt}`). "
                    f"Call `create_fact_edge` with source_fact_key=`{src}`, target_fact_key=`{tgt}`, "
                    "edge_type=`depends_on`."
                ),
            }
        )
        rows.append(
            {
                "prompt_id": f"dep_mutate_{dep_i:03d}",
                "conflict_class": "dependency_impact",
                "target_fact_key": tgt,
                "related_fact_key": src,
                "project_name": project_name,
                "mcp_tool": "memory_upsert_fact_v1",
                "deterministic_upsert": {
                    "kind": kind_from_category(str(tgt_f.get("category") or "decision")),
                    "key": tgt,
                    "body": new_upstream_body,
                    "tier": 1,
                    "tags": ["live_inject", "dependency_impact"],
                    "source_type": "synthetic",
                    "actor": "conflict_prompt_agent",
                    "confidence": 0.88,
                    "expected_version": None,
                },
                "agent_prompt": (
                    f"{pid_note} After edge `{src}` → depends_on → `{tgt}`, **update** upstream fact "
                    f"`{tgt}` with a new body that contradicts what downstream `{src}` assumes "
                    f"(dependency impact). Suggested body: {new_upstream_body[:500]}…"
                ),
            }
        )
        dep_i += 1
        if dep_i >= 15:
            break

    # --- Constraint: from SKF rules ---
    for ri, rule in enumerate(rules[:20]):
        name = str(rule.get("name") or f"rule_{ri}")
        desc = str(rule.get("description") or rule.get("condition") or "")
        rows.append(
            {
                "prompt_id": f"constraint_{ri:03d}",
                "conflict_class": "constraint_violation",
                "target_rule": name,
                "project_name": project_name,
                "mcp_tool": "memory_upsert_fact_v1",
                "deterministic_upsert": {
                    "kind": "constraint",
                    "key": f"live_inject.violation.{slug(name)}.{ri:03d}",
                    "body": f"Declared violation of rule '{name}': explicitly do the opposite of: {desc[:2000]}",
                    "tier": 1,
                    "tags": ["live_inject", "constraint_violation", f"rule:{slug(name)}"],
                    "source_type": "synthetic",
                    "actor": "conflict_prompt_agent",
                    "confidence": 0.8,
                },
                "agent_prompt": (
                    f"{pid_note} Rule from extraction: `{name}` — {desc[:800]}\n"
                    "Add a fact that **violates** this rule (numeric caps: exceed them; auth rules: assert insecure bypass). "
                    "Use `memory_upsert_fact_v1`. If the project has `upsert_project_constraint`, align violation with an active constraint."
                ),
            }
        )

    # --- Pad with extra semantic variants until min_prompts ---
    v = 0
    while len(rows) < min_prompts and facts:
        f = facts[v % len(facts)]
        k = f.get("key") or f"fact.{v}"
        val = str(f.get("value") or "")
        cat = str(f.get("category") or "other")
        new_key = f"live_inject.semantic_pad.{slug(k)}.{v:03d}"
        rows.append(
            {
                "prompt_id": f"semantic_pad_{v:03d}",
                "conflict_class": "semantic_contradiction",
                "target_fact_key": k,
                "project_name": project_name,
                "mcp_tool": "memory_upsert_fact_v1",
                "deterministic_upsert": {
                    "kind": kind_from_category(cat),
                    "key": new_key,
                    "body": opposite_stub(opposite_stub(val))[:12000],
                    "tier": 1,
                    "tags": ["live_inject", "semantic_contradiction", "padded"],
                    "source_type": "synthetic",
                    "actor": "conflict_prompt_agent",
                    "confidence": 0.82,
                },
                "agent_prompt": (
                    f"{pid_note} (Padded) Cross-key contradiction against `{k}`: write a second narrative "
                    "that an architect would reject if both were true."
                ),
            }
        )
        v += 1

    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skf", type=Path, required=True, help="Path to SKF v1.2 JSON")
    ap.add_argument("--out", type=Path, required=True, help="Output JSONL path")
    ap.add_argument("--min-prompts", type=int, default=45)
    ap.add_argument("--project-id", type=str, default="", help="Echo into prompts for MCP agents")
    args = ap.parse_args()

    data = load_skf(args.skf)
    rows = build_prompts(data, args.project_id.strip(), args.min_prompts)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"Wrote {len(rows)} prompts to {args.out}")


if __name__ == "__main__":
    main()
