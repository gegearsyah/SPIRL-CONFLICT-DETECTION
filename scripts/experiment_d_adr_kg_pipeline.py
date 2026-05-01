#!/usr/bin/env python3
"""
Experiment D — Real ADR corpus → Spirl knowledge graph (memory_upsert_fact_v1) + Phase-2-style conflicts.

Reads Markdown under ``external/architecture-decision-record/``, extracts decision/context/constraints
per file, upserts tagged facts into the project from ``.spirl/config.json`` → ``adr_reference_project_id``.

Logs (separate from synthetic C / ADR observation track):
  research/paper3_checkpoints.experiment_D.jsonl
  research/paper3_execution_log.experiment_D.jsonl

Usage (repo root or from ``Beyond Temporal Contradiction/scripts``)::

  python experiment_d_adr_kg_pipeline.py --baseline --scope en
  python experiment_d_adr_kg_pipeline.py --baseline --scope all --max-files 200
  python experiment_d_adr_kg_pipeline.py --conflicts
  python experiment_d_adr_kg_pipeline.py --baseline --conflicts --dry-run

Phase-2-style injections (``--conflicts``) mirror ``research_prompt/paper3_phase2_prompt.md`` classes
using **corpus-grounded** contradictory pairs (PostgreSQL vs MySQL, React vs Vue, etc.), plus dependency
edges, a numeric project constraint violation, and optional temporal same-key overlap.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from adr_corpus_mcp_pipeline import (  # noqa: E402
    McpSession,
    adr_root,
    append_jsonl,
    iso_now,
    load_json,
    mcp_from_config,
    read_adr_project_id,
    research_dir,
    save_last_response,
    spirl_config_path,
)

MAX_BODY = 12_000
# Root README is huge; full embeds per fact are slow. Shorter slice for the `.document` fact.
MAX_DOC_SLICE = 8_000
AGENT = "experiment_d_adr_pipeline"
EXP = {"id": "D", "architecture_label": "adr_real_kg_phase2", "dataset": "external/architecture-decision-record"}


def ckpt_log_paths() -> tuple[Path, Path]:
    r = research_dir()
    return r / "paper3_checkpoints.experiment_D.jsonl", r / "paper3_execution_log.experiment_D.jsonl"


def norm_header(h: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", h.lower()).strip()


def extract_sections(md: str) -> dict[str, str]:
    """Split on ## headers; map rough categories."""
    lines = md.splitlines()
    title = ""
    for line in lines[:30]:
        if line.startswith("# ") and not title:
            title = line[2:].strip()
            break
    sections: dict[str, list[str]] = {}
    current = "_preamble"
    sections[current] = []
    header_re = re.compile(r"^##\s+(.+)\s*$")
    for line in lines:
        m = header_re.match(line)
        if m:
            current = m.group(1).strip()
            sections.setdefault(current, [])
            continue
        sections.setdefault(current, []).append(line)
    flat: dict[str, str] = {"title": title, "_preamble": "\n".join(sections.get("_preamble", [])).strip()}
    for name, body_lines in sections.items():
        if name == "_preamble":
            continue
        flat[name] = "\n".join(body_lines).strip()
    return flat


def bucket_section(name: str) -> str | None:
    n = norm_header(name)
    if any(x in n for x in ("context", "background", "problem")):
        return "context"
    if any(x in n for x in ("decision", "status")):
        return "decision" if "status" not in n or "decision" in n else "status"
    if n.strip() == "status" or n.startswith("status"):
        return "status"
    if "decision" in n:
        return "decision"
    if any(x in n for x in ("consequence", "outcome", "implication")):
        return "consequences"
    if any(x in n for x in ("rationale", "justification", "reason")):
        return "rationale"
    if "alternative" in n or "option" in n:
        return "alternatives"
    if "constraint" in n or "requirement" in n:
        return "constraints"
    return None


def build_facts_for_file(rel_posix: str, text: str, doc_slice_max: int) -> list[dict[str, Any]]:
    """Return list of upsert payloads (without project_id): kind, key, body, tags, metadata."""
    sections = extract_sections(text)
    stem = rel_posix[:-3] if rel_posix.lower().endswith(".md") else rel_posix
    base_key = "adr." + re.sub(r"[^a-zA-Z0-9._-]+", "_", stem.replace("/", "."))[:120]
    tags_base = ["experiment_d", "adr_corpus", f"source:{rel_posix}"]
    out: list[dict[str, Any]] = []

    title = sections.get("title") or rel_posix
    meta = {
        "source_relpath": rel_posix,
        "title": title[:500],
    }

    # Whole-doc documentation spine (tier 3)
    doc_body = text.strip()[:MAX_BODY]
    out.append(
        {
            "kind": "documentation",
            "key": f"{base_key}.document",
            "body": f"ADR corpus file `{rel_posix}`.\n\n# {title}\n\n{doc_body}",
            "tier": 3,
            "tags": tags_base + ["kind:documentation"],
            "metadata": {**meta, "role": "full_markdown_slice"},
            "source_type": "import",
            "actor": AGENT,
            "confidence": 0.9,
        }
    )

    buckets: dict[str, str] = {}
    for sec_name, sec_body in sections.items():
        if sec_name in ("title", "_preamble") or not sec_body.strip():
            continue
        b = bucket_section(sec_name)
        if b:
            buckets[b] = (buckets.get(b, "") + "\n\n## " + sec_name + "\n\n" + sec_body).strip()

    if buckets.get("context"):
        out.append(
            {
                "kind": "research",
                "key": f"{base_key}.context",
                "body": buckets["context"][:MAX_BODY],
                "tier": 2,
                "tags": tags_base + ["kind:context"],
                "metadata": {**meta, "facet": "context"},
                "source_type": "import",
                "actor": AGENT,
                "confidence": 0.88,
            }
        )

    if buckets.get("decision"):
        out.append(
            {
                "kind": "decision",
                "key": f"{base_key}.decision",
                "body": buckets["decision"][:MAX_BODY],
                "tier": 1,
                "tags": tags_base + ["kind:decision"],
                "metadata": {**meta, "facet": "decision"},
                "source_type": "import",
                "actor": AGENT,
                "confidence": 0.92,
            }
        )

    if buckets.get("status"):
        out.append(
            {
                "kind": "constraint",
                "key": f"{base_key}.status",
                "body": f"Record status / lifecycle: {buckets['status'][:8000]}",
                "tier": 2,
                "tags": tags_base + ["kind:constraint", "adr_status"],
                "metadata": {**meta, "facet": "status"},
                "source_type": "import",
                "actor": AGENT,
                "confidence": 0.85,
            }
        )

    if buckets.get("constraints"):
        out.append(
            {
                "kind": "constraint",
                "key": f"{base_key}.constraints",
                "body": buckets["constraints"][:MAX_BODY],
                "tier": 2,
                "tags": tags_base + ["kind:constraint"],
                "metadata": {**meta, "facet": "constraints"},
                "source_type": "import",
                "actor": AGENT,
                "confidence": 0.9,
            }
        )

    cons = "\n\n".join(
        f"## {k}\n{buckets[k]}"
        for k in ("rationale", "consequences", "alternatives")
        if buckets.get(k)
    )
    if cons.strip():
        out.append(
            {
                "kind": "decision",
                "key": f"{base_key}.rationale_consequences",
                "body": cons[:MAX_BODY],
                "tier": 2,
                "tags": tags_base + ["kind:decision", "rationale"],
                "metadata": {**meta, "facet": "rationale_consequences"},
                "source_type": "import",
                "actor": AGENT,
                "confidence": 0.88,
            }
        )

    # Stack / tooling hints (single consolidated fact per file)
    stack_hits = detect_stack_hits(text)
    if stack_hits:
        out.append(
            {
                "kind": "other",
                "key": f"{base_key}.stack_and_dependencies",
                "body": "Observed technology references in this ADR markdown:\n- " + "\n- ".join(stack_hits),
                "tier": 2,
                "tags": tags_base + ["kind:stack", "dependencies"],
                "metadata": {**meta, "facet": "stack"},
                "source_type": "import",
                "actor": AGENT,
                "confidence": 0.75,
            }
        )

    # Spirl / agent role guidance from corpus CONTEXT (once per repo, keyed by file)
    if rel_posix == "CONTEXT.md":
        out.append(
            {
                "kind": "decision",
                "key": "adr.corpus.spirl_modeling_intent",
                "body": (
                    "From CONTEXT.md: Model this ADR library as architectural knowledge (decisions, options, "
                    "consequences). Preserve source path and title; cross-links may justify related_to / "
                    "depends_on edges. Use kinds decision, research, documentation per deployment constraints."
                ),
                "tier": 1,
                "tags": ["experiment_d", "spirl_policy", "kind:decision"],
                "metadata": meta,
                "source_type": "human",
                "actor": AGENT,
                "confidence": 1.0,
            }
        )

    return out


def detect_stack_hits(text: str) -> list[str]:
    t = text.lower()
    catalog = [
        ("postgresql", "PostgreSQL"),
        ("mysql", "MySQL"),
        ("mongodb", "MongoDB"),
        ("kubernetes", "Kubernetes"),
        ("docker", "Docker"),
        ("react", "React"),
        ("vue", "Vue"),
        ("svelte", "Svelte"),
        ("tailwind", "Tailwind CSS"),
        ("django", "Django"),
        ("rails", "Ruby on Rails"),
        ("playwright", "Playwright"),
        ("selenium", "Selenium"),
        ("azure", "Microsoft Azure"),
        ("gcp", "Google Cloud"),
        ("terraform", "Terraform"),
        ("npm", "npm / Node ecosystem"),
        ("python", "Python"),
        ("rust", "Rust"),
        ("go programming", "Go"),
        ("typescript", "TypeScript"),
    ]
    found: list[str] = []
    for needle, label in catalog:
        if needle in t and label not in found:
            found.append(label)
    return found[:40]


def collect_markdown_paths(root: Path, scope: str) -> list[Path]:
    paths: list[Path] = []
    if scope in ("en", "default"):
        for p in [root / "README.md", root / "CONTEXT.md"]:
            if p.is_file():
                paths.append(p)
        paths.extend(sorted((root / "locales" / "en").rglob("*.md")))
    elif scope == "all":
        paths.extend(sorted(root.rglob("*.md")))
    else:
        raise SystemExit(f"Unknown --scope {scope}")
    # de-dup, stable order
    seen: set[str] = set()
    out: list[Path] = []
    for p in paths:
        k = str(p.resolve())
        if k not in seen:
            seen.add(k)
            out.append(p)
    return out


def upsert_fact(mcp: McpSession, project_id: str, payload: dict[str, Any], dry_run: bool) -> Any:
    args = {"project_id": project_id, "product_id": "spirl", **payload}
    if dry_run:
        return {"dry_run": True, "args_keys": list(args.keys())}
    res = mcp.call_tool("memory_upsert_fact_v1", args)
    save_last_response(res)
    return res


def log_experiment(row: dict[str, Any]) -> None:
    _, logp = ckpt_log_paths()
    append_jsonl(
        logp,
        {
            "timestamp": iso_now(),
            "experiment": EXP,
            **row,
        },
    )


def checkpoint(ctype: str, status: str, notes: str, **extra: Any) -> None:
    ckpt, _ = ckpt_log_paths()
    append_jsonl(
        ckpt,
        {
            "timestamp": iso_now(),
            "checkpoint_type": ctype,
            "agent_id": AGENT,
            "status": status,
            "experiment": EXP,
            "notes": notes,
            **extra,
        },
    )


def run_baseline(mcp: McpSession, project_id: str, scope: str, max_files: int | None, dry_run: bool) -> int:
    root = adr_root()
    md_paths = collect_markdown_paths(root, scope)
    if max_files is not None:
        md_paths = md_paths[: max(0, max_files)]

    checkpoint("baseline_start", "in_progress", f"Experiment D baseline — {len(md_paths)} markdown files", scope=scope)
    total_upserts = 0
    for path in md_paths:
        rel = path.relative_to(root).as_posix()
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            log_experiment({"agent_id": AGENT, "action": "file_read_failed", "project": project_id, "result": {"path": rel, "error": str(e)}})
            continue
        facts = build_facts_for_file(rel, text)
        for payload in facts:
            upsert_fact(mcp, project_id, payload, dry_run)
            total_upserts += 1
            log_experiment(
                {
                    "agent_id": AGENT,
                    "action": "baseline_upsert",
                    "project": project_id,
                    "result": {"source": rel, "key": payload["key"], "kind": payload["kind"]},
                }
            )
    checkpoint(
        "baseline_complete",
        "complete",
        f"Baseline upserts: {total_upserts}",
        file_count=len(md_paths),
        upserts=total_upserts,
    )
    return total_upserts


def groundtruth_upsert(
    mcp: McpSession,
    project_id: str,
    injection_number: int,
    body: dict[str, Any],
    dry_run: bool,
) -> None:
    payload = {
        "kind": "research",
        "key": f"research.experiment_d.groundtruth.{injection_number}",
        "body": json.dumps(body, ensure_ascii=False),
        "tier": 3,
        "tags": ["experiment_d", "groundtruth", "research"],
        "metadata": {"experiment": "D"},
        "source_type": "synthetic",
        "actor": AGENT,
        "confidence": 1.0,
        "skip_embedding": True,
        "skip_conflict_check": True,
    }
    upsert_fact(mcp, project_id, payload, dry_run)


def run_conflicts(mcp: McpSession, project_id: str, dry_run: bool) -> None:
    """
    Corpus-grounded Phase-2-style set (not 200): semantic pairs, dependency edge, constraint, temporal.
    """
    checkpoint("phase2_conflicts_start", "in_progress", "Experiment D — conflict injection (Phase-2 classes)")
    inj = 0

    def inject_pair(
        class_name: str,
        a: dict[str, Any],
        b: dict[str, Any],
    ) -> None:
        nonlocal inj
        inj += 1
        n = inj
        if not dry_run:
            ra = upsert_fact(mcp, project_id, a, False)
            rb = upsert_fact(mcp, project_id, b, False)
            det = {}
            if isinstance(rb, dict):
                det = rb.get("detection") or {}
        else:
            ra = rb = {}
            det = {}
        log_experiment(
            {
                "agent_id": AGENT,
                "phase": 2,
                "action": "conflict_injected",
                "project": project_id,
                "injection_number": n,
                "conflict_class": class_name,
                "result": {
                    "fact_keys": [a["key"], b["key"]],
                    "detection_latency_ms": det.get("detection_latency_ms"),
                    "conflicts_detected": det.get("conflicts_detected"),
                    "success": True,
                },
            }
        )
        groundtruth_upsert(
            mcp,
            project_id,
            n,
            {
                "conflict_number": n,
                "class": class_name,
                "project": project_id,
                "fact_keys_involved": [a["key"], b["key"]],
                "corpus_note": "Derived from opposing ADR example topics in joelparkerhenderson corpus",
            },
            dry_run,
        )

    # Class 1 — semantic contradiction (different keys, same concern)
    inject_pair(
        "semantic_contradiction",
        {
            "kind": "decision",
            "key": "corpus.db.primary_store.postgres_style",
            "body": "Primary transactional store: PostgreSQL is the org standard for new services (ACID, advanced SQL).",
            "tier": 1,
            "tags": ["experiment_d", "semantic_conflict_seed", "postgresql"],
            "source_type": "import",
            "actor": AGENT,
            "confidence": 0.9,
        },
        {
            "kind": "decision",
            "key": "data.platform.document_first.standard",
            "body": "Primary persistence layer: MongoDB as the default document store for all greenfield apps.",
            "tier": 1,
            "tags": ["experiment_d", "semantic_conflict_seed", "mongodb"],
            "source_type": "import",
            "actor": AGENT,
            "confidence": 0.9,
        },
    )
    inject_pair(
        "semantic_contradiction",
        {
            "kind": "decision",
            "key": "ui.framework.standard.react",
            "body": "Front-end standard: React for all product SPAs.",
            "tier": 1,
            "tags": ["experiment_d", "semantic_conflict_seed", "react"],
            "source_type": "import",
            "actor": AGENT,
            "confidence": 0.9,
        },
        {
            "kind": "decision",
            "key": "client.rendering.primary.vue",
            "body": "Front-end standard: Vue 3 for all product SPAs.",
            "tier": 1,
            "tags": ["experiment_d", "semantic_conflict_seed", "vue"],
            "source_type": "import",
            "actor": AGENT,
            "confidence": 0.9,
        },
    )

    # Class 2 — dependency impact: downstream depends on upstream, then upstream contradicted
    inj += 1
    n = inj
    up = {
        "kind": "decision",
        "key": "exp_d.auth.mechanism",
        "body": "API authentication uses JWT bearer tokens issued by the central IdP.",
        "tier": 1,
        "tags": ["experiment_d", "dependency_chain"],
        "source_type": "import",
        "actor": AGENT,
        "confidence": 0.95,
    }
    down = {
        "kind": "decision",
        "key": "exp_d.feature.mobile_client.assumption",
        "body": "Mobile clients attach Authorization: Bearer <jwt> on every API call.",
        "tier": 2,
        "tags": ["experiment_d", "dependency_chain"],
        "source_type": "import",
        "actor": AGENT,
        "confidence": 0.9,
    }
    if not dry_run:
        upsert_fact(mcp, project_id, up, False)
        upsert_fact(mcp, project_id, down, False)
        mcp.call_tool(
            "create_fact_edge",
            {
                "project_id": project_id,
                "source_fact_key": down["key"],
                "target_fact_key": up["key"],
                "edge_type": "depends_on",
                "metadata": {"experiment": "D", "class": "dependency_impact"},
            },
        )
        ru = upsert_fact(
            mcp,
            project_id,
            {
                **up,
                "body": "API authentication uses opaque server-side session cookies only; no JWTs.",
            },
            False,
        )
        det = ru.get("detection") if isinstance(ru, dict) else {}
    else:
        det = {}
    log_experiment(
        {
            "agent_id": AGENT,
            "phase": 2,
            "action": "conflict_injected",
            "project": project_id,
            "injection_number": n,
            "conflict_class": "dependency_impact",
            "result": {
                "fact_keys": [up["key"], down["key"]],
                "detection_latency_ms": det.get("detection_latency_ms") if isinstance(det, dict) else None,
                "conflicts_detected": det.get("conflicts_detected") if isinstance(det, dict) else None,
                "success": True,
            },
        }
    )
    groundtruth_upsert(
        mcp,
        project_id,
        n,
        {"conflict_number": n, "class": "dependency_impact", "fact_keys_involved": [up["key"], down["key"]]},
        dry_run,
    )

    # Class 3 — constraint violation
    inj += 1
    n = inj
    if not dry_run:
        mcp.call_tool(
            "upsert_project_constraint",
            {
                "project_id": project_id,
                "constraint_type": "numeric_cap",
                "label": "max_supported_languages",
                "value": 3.0,
                "unit": "count",
                "description": "No more than 3 primary programming languages in the ADR reference rollout.",
                "enabled": True,
            },
        )
        rv = upsert_fact(
            mcp,
            project_id,
            {
                "kind": "other",
                "key": "exp_d.language.diversity.rollout",
                "body": "We officially standardize on six primary languages in this corpus rollout: Python, Go, Rust, Java, Ruby, and TypeScript.",
                "tier": 2,
                "tags": ["experiment_d", "constraint_violation_seed"],
                "source_type": "import",
                "actor": AGENT,
                "confidence": 0.8,
            },
            False,
        )
        det = rv.get("detection") if isinstance(rv, dict) else {}
    else:
        det = {}
    log_experiment(
        {
            "agent_id": AGENT,
            "phase": 2,
            "action": "conflict_injected",
            "project": project_id,
            "injection_number": n,
            "conflict_class": "constraint_violation",
            "result": {
                "fact_keys": ["exp_d.language.diversity.rollout"],
                "detection_latency_ms": det.get("detection_latency_ms") if isinstance(det, dict) else None,
                "conflicts_detected": det.get("conflicts_detected") if isinstance(det, dict) else None,
                "success": True,
            },
        }
    )
    groundtruth_upsert(
        mcp,
        project_id,
        n,
        {"conflict_number": n, "class": "constraint_violation", "fact_keys_involved": ["exp_d.language.diversity.rollout"]},
        dry_run,
    )

    # Class 4 — temporal invalidation (same key, overlapping windows if server accepts valid_from/until)
    inj += 1
    n = inj
    tk = "exp_d.orchestration.platform.primary"
    t_a = {
        "kind": "decision",
        "key": tk,
        "body": "Primary container orchestration: Kubernetes.",
        "tier": 1,
        "tags": ["experiment_d", "temporal_seed", "kubernetes"],
        "source_type": "import",
        "actor": AGENT,
        "confidence": 0.9,
        "valid_from": "2026-01-01T00:00:00Z",
        "valid_until": "2026-12-31T23:59:59Z",
    }
    t_b = {
        "kind": "decision",
        "key": tk,
        "body": "Primary container orchestration: Docker Swarm.",
        "tier": 1,
        "tags": ["experiment_d", "temporal_seed", "docker_swarm"],
        "source_type": "import",
        "actor": AGENT,
        "confidence": 0.9,
        "valid_from": "2026-06-01T00:00:00Z",
        "valid_until": "2027-12-31T23:59:59Z",
    }
    if not dry_run:
        r1 = upsert_fact(mcp, project_id, t_a, False)
        r2 = upsert_fact(mcp, project_id, t_b, False)
        det = r2.get("detection") if isinstance(r2, dict) else {}
    else:
        det = {}
    log_experiment(
        {
            "agent_id": AGENT,
            "phase": 2,
            "action": "conflict_injected",
            "project": project_id,
            "injection_number": n,
            "conflict_class": "temporal_invalidation",
            "result": {
                "fact_keys": [tk, tk],
                "detection_latency_ms": det.get("detection_latency_ms") if isinstance(det, dict) else None,
                "conflicts_detected": det.get("conflicts_detected") if isinstance(det, dict) else None,
                "success": True,
            },
        }
    )
    groundtruth_upsert(
        mcp,
        project_id,
        n,
        {"conflict_number": n, "class": "temporal_invalidation", "fact_keys_involved": [tk]},
        dry_run,
    )

    checkpoint("phase2_conflicts_complete", "complete", f"Experiment D conflict injections finished ({inj} groups)")


def main() -> None:
    ap = argparse.ArgumentParser(description="Experiment D — ADR corpus facts + Phase-2-style conflicts")
    ap.add_argument("--baseline", action="store_true", help="Upsert extracted facts from Markdown corpus")
    ap.add_argument("--conflicts", action="store_true", help="Run Phase-2-style conflict injections")
    ap.add_argument("--scope", choices=("en", "all"), default="en", help="en: README+CONTEXT+locales/en; all: every .md")
    ap.add_argument("--max-files", type=int, default=None, help="Cap files processed (baseline only)")
    ap.add_argument("--dry-run", action="store_true", help="Do not call MCP; log intended actions only")
    ap.add_argument("--project-id", type=str, default="", help="Override adr_reference_project_id")
    args = ap.parse_args()

    if not args.baseline and not args.conflicts:
        ap.print_help()
        sys.exit(2)

    cfg = load_json(spirl_config_path())
    project_id = args.project_id.strip() or read_adr_project_id(cfg)

    if not args.dry_run:
        mcp, _ = mcp_from_config()
        mcp.connect()
    else:
        mcp = None  # type: ignore[assignment]

    if args.baseline:
        assert mcp is not None or args.dry_run
        run_baseline(mcp, project_id, args.scope, args.max_files, args.dry_run)

    if args.conflicts:
        assert mcp is not None or args.dry_run
        run_conflicts(mcp, project_id, args.dry_run)

    print(f"Done. project_id={project_id} dry_run={args.dry_run}")


if __name__ == "__main__":
    main()
