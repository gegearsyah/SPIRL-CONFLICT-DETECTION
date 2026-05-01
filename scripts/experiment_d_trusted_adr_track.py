#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from adr_corpus_mcp_pipeline import adr_root, append_jsonl, iso_now, research_dir  # noqa: E402
from paper3_paths import btc_root  # noqa: E402

AGENT = "experiment_d_trusted_adr_track"

# When set (via --lab-root), all Experiment D artifacts go under ``<lab>/research/`` instead of ``BTC/research/``.
_LAB_ROOT: Path | None = None


def experiment_d_research_dir() -> Path:
    if _LAB_ROOT is not None:
        p = _LAB_ROOT / "research"
        p.mkdir(parents=True, exist_ok=True)
        return p
    return research_dir()


def _rel_to_btc(p: Path) -> str:
    try:
        return p.resolve().relative_to(btc_root().resolve()).as_posix()
    except ValueError:
        return p.resolve().as_posix()


def resolve_lab_root_arg(raw: str | None) -> Path | None:
    if not (raw or "").strip():
        return None
    p = Path(raw.strip())
    if not p.is_absolute():
        # Resolve relative to CWD so ``../trusted-adr-lab`` from ``scripts/`` stays under BTC.
        p = (Path.cwd() / p).resolve()
    return p.resolve()
EXP = {"id": "D", "architecture_label": "adr_real_trusted_track", "dataset": "external/architecture-decision-record"}
SOURCE_FAMILY = "adr_doc"
SOURCE_REPO = "architecture-decision-record"
SOURCE_REPO_URL = "https://github.com/joelparkerhenderson/architecture-decision-record"
SOURCE_RAW_BASE = "https://github.com/joelparkerhenderson/architecture-decision-record/blob/main/"
SOURCE_CORPUS_TYPE = "public_example_adr_corpus"
MAX_SNIPPET = 320

PAIR_RECIPES = [
    ("d-sem-01", "semantic_contradiction", "postgresql-database", "mysql-database", "trusted_adr.db.standard.mysql", "decision", "Primary database standard: MySQL is the preferred DBMS for the upcoming project.", "Conflicts with the PostgreSQL ADR while remaining grounded in the MySQL ADR decision.", "doc_pair_grounded"),
    ("d-sem-02", "semantic_contradiction", "react-front-end-javascript-library", "vue-front-end-javascript-library", "trusted_adr.frontend.library.vue", "decision", "Primary front-end library: Vue is the standard UI stack for the web application.", "Directly opposes the React ADR by asserting the alternative library's decision as the standard.", "doc_pair_grounded"),
    ("d-sem-03", "semantic_contradiction", "docker-swarm-container-orchestration", "kubernetes-container-orchestration", "trusted_adr.orchestration.kubernetes", "decision", "Primary container orchestration: Kubernetes is adopted as the enterprise standard for the application portfolio.", "Conflicts with the Docker Swarm ADR while staying anchored in the Kubernetes ADR decision.", "doc_pair_grounded"),
    ("d-sem-04", "semantic_contradiction", "python-django-framework", "ruby-on-rails-framework", "trusted_adr.web.framework.rails", "decision", "Primary web framework: Ruby on Rails is the standard framework for the application's core business workflows.", "Opposes the Django framework choice with another real ADR-backed framework decision.", "doc_pair_grounded"),
]

SINGLE_RECIPES = [
    ("d-con-01", "constraint_violation", "java-programming-language", "Consequences", "trusted_adr.java.runtime.non_jvm", "constraint", "Project services will be written in Java while targeting a non-JVM runtime environment for production execution.", "Violates the explicit consequence that Java code must remain compatible with the JVM.", "doc_exact"),
    ("d-con-02", "constraint_violation", "timestamp-format", "Decision", "trusted_adr.timestamps.local_seconds", "constraint", "Timestamp interoperability standard: use local-time strings with second precision as the default across systems.", "Violates the explicit ISO 8601 UTC nanosecond-format decision in the timestamp ADR.", "doc_exact"),
    ("d-tmp-01", "temporal_invalidation", "programming-languages", "Status", "trusted_adr.languages.backend.rollback", "decision", "Reopen the finalized language decision and roll the backend stack back from Rust to C++ for new services.", "Temporal rollback of a documented decided language selection.", "doc_interpreted"),
    ("d-tmp-02", "temporal_invalidation", "timestamp-format", "Status", "trusted_adr.timestamps.rollback.localtime", "decision", "Rollback the finalized timestamp standard from ISO 8601 UTC back to local-time-only formatting for all logs and APIs.", "Invalidates an already decided timestamp standard.", "doc_interpreted"),
    ("d-ben-01", "benign", "postgresql-database", "Decision", "trusted_adr.benign.postgresql", "decision", "For the upcoming project, PostgreSQL remains the preferred database management system.", "Straight paraphrase of the PostgreSQL ADR decision.", "doc_exact"),
    ("d-ben-02", "benign", "react-front-end-javascript-library", "Decision", "trusted_adr.benign.react", "decision", "The application's UI stack is built around React as the chosen front-end JavaScript library.", "Equivalent restatement of the React ADR decision.", "doc_exact"),
    ("d-ben-03", "benign", "kubernetes-container-orchestration", "Decision Made", "trusted_adr.benign.kubernetes", "decision", "Kubernetes remains the selected orchestration platform for the cloud-native application portfolio.", "Aligned paraphrase of the Kubernetes ADR decision outcome.", "doc_exact"),
    ("d-ben-04", "benign", "python-django-framework", "Decision", "trusted_adr.benign.django", "decision", "Django is the adopted framework for the customer-data web application because it offers a broad built-in feature set.", "Consistent restatement of the Django ADR decision and factors.", "doc_exact"),
    ("d-ben-05", "benign", "timestamp-format", "Decision", "trusted_adr.benign.timestamps", "constraint", "Systems should serialize timestamps using ISO 8601 in UTC with nanosecond precision.", "Directly aligned with the timestamp ADR standard.", "doc_exact"),
    ("d-ben-06", "benign", "programming-languages", "Decision", "trusted_adr.benign.languages", "decision", "TypeScript stays the front-end choice and Rust stays the back-end choice in the current language strategy.", "Faithful summary of the programming-languages decision.", "doc_exact"),
    ("d-amb-01", "needs_review", "sveltekit-framework", "Alternatives Considered", "trusted_adr.review.react_microsite", "decision", "For a small internal microsite, React could remain an acceptable alternative even if SvelteKit is the current default choice.", "Lists React and Vue as considered alternatives, so this should pressure review rather than forced typed conflict.", "doc_interpreted"),
    ("d-amb-02", "needs_review", "web-application-framework-batteries-included-full-stack-for-a-startup-product", "Frameworks Evaluated", "trusted_adr.review.rails_internal_tool", "decision", "Ruby on Rails may still be a defensible choice for an internal tool where AI/ML integration is not a primary requirement.", "Rails is a serious alternative in the source ADR, making this a bounded review case.", "doc_interpreted"),
    ("d-amb-03", "needs_review", "programming-languages", "Status", "trusted_adr.review.go_backend", "decision", "A later proposal to introduce Go for a specific backend service should trigger decision review rather than immediate rejection.", "The ADR says the current choice is decided but also explicitly open to new alternatives.", "doc_interpreted"),
    ("d-amb-04", "needs_review", "timestamp-format", "Positions", "trusted_adr.review.localtime_boundary", "constraint", "At a boundary with legacy regional systems, local-time timestamp strings may still be acceptable for a narrow integration bridge.", "The ADR explicitly discusses local time as a position, but the chosen standard still prefers UTC ISO 8601.", "doc_interpreted"),
]


def ckpt_log_paths() -> tuple[Path, Path]:
    r = experiment_d_research_dir()
    return r / "paper3_checkpoints.experiment_D.jsonl", r / "paper3_execution_log.experiment_D.jsonl"


def trusted_dir() -> Path:
    p = experiment_d_research_dir() / "trusted_adr"
    p.mkdir(parents=True, exist_ok=True)
    return p


def paths() -> dict[str, Path]:
    base = trusted_dir()
    return {
        "corpus_manifest": base / "adr_corpus_manifest.jsonl",
        "fact_manifest": base / "adr_extracted_fact_manifest.jsonl",
        "conflicts": base / "trusted_conflict_rows.jsonl",
        "benign": base / "trusted_benign_rows.jsonl",
        "ambiguity": base / "trusted_ambiguity_rows.jsonl",
        "audit": base / "trusted_manual_audit_sample.jsonl",
        "readme": base / "README.md",
        "links": base / "trusted_source_links.md",
    }


def log_event(action: str, **result: Any) -> None:
    _, logp = ckpt_log_paths()
    append_jsonl(logp, {"timestamp": iso_now(), "experiment": EXP, "agent_id": AGENT, "action": action, "result": result})


def checkpoint(kind: str, notes: str, **extra: Any) -> None:
    ckpt, _ = ckpt_log_paths()
    append_jsonl(ckpt, {"timestamp": iso_now(), "experiment": EXP, "agent_id": AGENT, "checkpoint_type": kind, "status": "complete", "notes": notes, **extra})


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "\n".join(json.dumps(row, ensure_ascii=False) for row in rows)
    path.write_text((text + "\n") if text else "", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def normalize_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def truncate(text: str, limit: int = MAX_SNIPPET) -> str:
    text = normalize_ws(text)
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def norm_header(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def extract_sections(md: str) -> dict[str, str]:
    lines = md.splitlines()
    title = ""
    for line in lines[:30]:
        if line.startswith("# "):
            title = line[2:].strip()
            break
    sections: dict[str, list[str]] = {"_preamble": []}
    current = "_preamble"
    header_re = re.compile(r"^##\s+(.+?)\s*$")
    for line in lines:
        m = header_re.match(line)
        if m:
            current = m.group(1).strip()
            sections.setdefault(current, [])
            continue
        sections.setdefault(current, []).append(line)
    flat = {"title": title}
    for name, body_lines in sections.items():
        flat[name] = "\n".join(body_lines).strip()
    return flat


def collect_paths(scope: str, max_files: int | None) -> list[Path]:
    root = adr_root()
    if scope == "all":
        candidates = sorted(root.rglob("*.md"))
    else:
        candidates = [p for p in [root / "README.md", root / "CONTEXT.md"] if p.is_file()]
        candidates += sorted((root / "locales" / "en").rglob("*.md"))
    if max_files is not None:
        candidates = candidates[: max(0, max_files)]
    return candidates


def rel_slug(root: Path, path: Path) -> str:
    rel = path.relative_to(root).as_posix()
    p = Path(rel)
    return p.parent.name.lower() if p.name.lower() == "index.md" else p.stem.lower()


def git_head_for_file(root: Path, rel: str) -> str | None:
    try:
        proc = subprocess.run(["git", "-C", str(root), "log", "-n", "1", "--format=%H", "--", rel], capture_output=True, text=True, check=False, timeout=20)
    except (OSError, subprocess.TimeoutExpired):
        return None
    sha = (proc.stdout or "").strip()
    return sha or None


def source_url(path: str) -> str:
    return SOURCE_RAW_BASE + path.replace("\\", "/")


def section_text(record: dict[str, Any], target: str) -> str:
    target_norm = norm_header(target)
    for name, body in record["sections"].items():
        if norm_header(name) == target_norm:
            return body
    aliases = {
        "decision made": "decision",
        "alternatives considered": "alternatives",
        "frameworks evaluated": "preamble",
    }
    alias = aliases.get(target_norm)
    if alias == "decision":
        for name, body in record["sections"].items():
            if "decision" in norm_header(name):
                return body
    if alias == "alternatives":
        for name, body in record["sections"].items():
            if "alternative" in norm_header(name) or "position" in norm_header(name):
                return body
    if alias == "preamble":
        return record["sections"].get("_preamble", "")
    return ""


def collect_records(scope: str, max_files: int | None) -> list[dict[str, Any]]:
    root = adr_root()
    out: list[dict[str, Any]] = []
    for path in collect_paths(scope, max_files):
        rel = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8", errors="replace")
        sections = extract_sections(text)
        out.append(
            {
                "slug": rel_slug(root, path),
                "source_path": rel,
                "source_commit": git_head_for_file(root, rel),
                "title": sections.get("title") or rel,
                "sections": sections,
                "text": text,
            }
        )
    return out


def build_source_ref(record: dict[str, Any], section: str | None) -> dict[str, Any]:
    evidence = section_text(record, section or "") if section else ""
    if not evidence:
        evidence = record["sections"].get("_preamble", "") or record["text"]
    return {
        "source_family": SOURCE_FAMILY,
        "source_repo": SOURCE_REPO,
        "source_repo_url": SOURCE_REPO_URL,
        "source_url": source_url(record["source_path"]),
        "source_corpus_type": SOURCE_CORPUS_TYPE,
        "source_path": record["source_path"],
        "source_section": section or "Document",
        "source_commit": record["source_commit"],
        "evidence_snippet": truncate(evidence),
    }


def build_fact_manifest(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for record in records:
        for section in ("Decision", "Status", "Consequences", "Alternatives", "Constraints", "Context"):
            body = section_text(record, section)
            if body:
                rows.append(
                    {
                        "fact_key": f"trusted_adr.fact.{record['slug']}.{norm_header(section).replace(' ', '_')}",
                        "kind": "decision" if section in {"Decision", "Consequences", "Alternatives"} else "research",
                        "source_family": SOURCE_FAMILY,
                        "source_repo": SOURCE_REPO,
                        "source_repo_url": SOURCE_REPO_URL,
                        "source_url": source_url(record["source_path"]),
                        "source_corpus_type": SOURCE_CORPUS_TYPE,
                        "source_path": record["source_path"],
                        "source_section": section,
                        "source_commit": record["source_commit"],
                        "evidence_snippet": truncate(body),
                        "provenance_level": "doc_exact",
                        "review_status": "unreviewed",
                    }
                )
    return rows


def make_row(row_id: str, expected_label: str, proposal_key: str, kind: str, body: str, rationale: str, sources: list[dict[str, Any]], provenance_level: str) -> dict[str, Any]:
    group = "trusted_conflict"
    if expected_label == "benign":
        group = "trusted_benign"
    elif expected_label == "needs_review":
        group = "trusted_ambiguity"
    return {
        "row_id": row_id,
        "track": "experiment_D_trusted_adr",
        "row_group": group,
        "expected_label": expected_label,
        "expected_class": expected_label if expected_label in {"semantic_contradiction", "constraint_violation", "dependency_impact", "temporal_invalidation"} else None,
        "proposed_fact": {"key": proposal_key, "kind": kind, "body": body, "valid_from": None, "valid_until": None},
        "source_family": SOURCE_FAMILY,
        "source_repo": SOURCE_REPO,
        "source_repo_url": SOURCE_REPO_URL,
        "source_corpus_type": SOURCE_CORPUS_TYPE,
        "source_path": [s["source_path"] for s in sources],
        "source_urls": [s["source_url"] for s in sources],
        "source_section": [s["source_section"] for s in sources],
        "source_commit": [s["source_commit"] for s in sources],
        "evidence_snippet": [s["evidence_snippet"] for s in sources],
        "provenance_level": provenance_level,
        "review_status": "unreviewed",
        "based_on_sources": sources,
        "rationale": rationale,
    }


def build_row_sets(records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    by_slug = {record["slug"]: record for record in records}
    conflicts: list[dict[str, Any]] = []
    benign: list[dict[str, Any]] = []
    ambiguity: list[dict[str, Any]] = []

    for row_id, label, left_slug, right_slug, proposal_key, kind, body, rationale, provenance_level in PAIR_RECIPES:
        left = by_slug.get(left_slug)
        right = by_slug.get(right_slug)
        if left and right:
            conflicts.append(make_row(row_id, label, proposal_key, kind, body, rationale, [build_source_ref(left, "Decision"), build_source_ref(right, "Decision")], provenance_level))

    for row_id, label, slug, section, proposal_key, kind, body, rationale, provenance_level in SINGLE_RECIPES:
        record = by_slug.get(slug)
        if not record:
            continue
        row = make_row(row_id, label, proposal_key, kind, body, rationale, [build_source_ref(record, section)], provenance_level)
        if label == "benign":
            benign.append(row)
        elif label == "needs_review":
            ambiguity.append(row)
        else:
            conflicts.append(row)
    return conflicts, benign, ambiguity


def audit_sample(conflicts: list[dict[str, Any]], benign: list[dict[str, Any]], ambiguity: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sample: list[dict[str, Any]] = []
    for rows in (conflicts, benign, ambiguity):
        if rows:
            sample.extend(rows[: max(1, (len(rows) + 4) // 5)])
    return sample


def write_reports(records: list[dict[str, Any]], fact_rows: list[dict[str, Any]], conflicts: list[dict[str, Any]], benign: list[dict[str, Any]], ambiguity: list[dict[str, Any]], audit_rows: list[dict[str, Any]]) -> None:
    rd = experiment_d_research_dir()
    rel = _rel_to_btc(rd)
    write_text(rd / "paper3_phase1_report.experiment_D.md", f"""# Experiment D - trusted ADR baseline

- Source repo: `{SOURCE_REPO}`
- Source repo URL: {SOURCE_REPO_URL}
- Corpus type: `{SOURCE_CORPUS_TYPE}`
- Markdown files selected: **{len(records)}**
- Extracted fact manifest rows: **{len(fact_rows)}**
- Provenance coverage: **100%**
- Artifacts: `{rel}/trusted_adr/adr_corpus_manifest.jsonl`, `{rel}/trusted_adr/adr_extracted_fact_manifest.jsonl`, `{rel}/trusted_adr/trusted_source_links.md`

Caveat:

- this is a public ADR example corpus, not a private enterprise-internal ADR archive
""")
    typed_counts = Counter(row["expected_label"] for row in conflicts)
    write_text(rd / "paper3_phase2_report.experiment_D.md", f"""# Experiment D - trusted ADR row sets

- Trusted conflict rows: **{len(conflicts)}**
- Trusted benign rows: **{len(benign)}**
- Trusted ambiguity rows: **{len(ambiguity)}**
- `semantic_contradiction`: **{typed_counts.get('semantic_contradiction', 0)}**
- `constraint_violation`: **{typed_counts.get('constraint_violation', 0)}**
- `dependency_impact`: **{typed_counts.get('dependency_impact', 0)}**
- `temporal_invalidation`: **{typed_counts.get('temporal_invalidation', 0)}**
- Ambiguity rows are `needs_review` pressure only and remain separate from typed conflict scoring.
- Exact row-level GitHub source URLs are listed in `{rel}/trusted_adr/trusted_source_links.md`.
""")
    write_text(rd / "paper3_phase3_report.experiment_D.md", f"""# Experiment D - trusted ADR audit sample

- Audit sample rows: **{len(audit_rows)}**
- Artifact: `{rel}/trusted_adr/trusted_manual_audit_sample.jsonl`
- Audit every row against its evidence snippet, `source_url`, and local `source_path`.
""")
    write_text(rd / "paper3_trusted_adr_summary.md", f"""# Experiment D - trusted ADR standalone summary

- Upstream repo: {SOURCE_REPO_URL}
- Corpus type: `{SOURCE_CORPUS_TYPE}`
- Corpus files: **{len(records)}**
- Fact manifest rows: **{len(fact_rows)}**
- Trusted conflict rows: **{len(conflicts)}**
- Trusted benign rows: **{len(benign)}**
- Trusted ambiguity rows: **{len(ambiguity)}**
- Manual audit sample: **{len(audit_rows)}**

This track is standalone and does not merge into `real-data-lab/research/*`.
""")


def write_source_links(conflicts: list[dict[str, Any]], benign: list[dict[str, Any]], ambiguity: list[dict[str, Any]]) -> None:
    lines = [
        "# Trusted ADR source links",
        "",
        f"Upstream repo: {SOURCE_REPO_URL}",
        f"Corpus type: `{SOURCE_CORPUS_TYPE}`",
        "",
        "These rows are grounded in public ADR example documents. Use this file when citing exact source URLs in the paper or notes.",
        "",
    ]
    for title, rows in (("Conflict rows", conflicts), ("Benign rows", benign), ("Ambiguity rows", ambiguity)):
        lines.append(f"## {title}")
        lines.append("")
        for row in rows:
            lines.append(f"- `{row['row_id']}`")
            for url in row.get("source_urls", []):
                lines.append(f"  - {url}")
        lines.append("")
    write_text(paths()["links"], "\n".join(lines))


def write_readme() -> None:
    p = paths()
    write_text(p["readme"], """# Trusted ADR artifacts\n\nStandalone Experiment D artifacts generated from the local ADR corpus.\n\n- `adr_corpus_manifest.jsonl`: source files used\n- `adr_extracted_fact_manifest.jsonl`: extracted source-backed fact rows\n- `trusted_conflict_rows.jsonl`: typed conflict rows\n- `trusted_benign_rows.jsonl`: benign rows\n- `trusted_ambiguity_rows.jsonl`: `needs_review` pressure rows\n- `trusted_manual_audit_sample.jsonl`: deterministic audit sample\n\nThese files stay separate from the live mixed RDL benchmark.\n""")


def main() -> None:
    global _LAB_ROOT

    ap = argparse.ArgumentParser(description="Standalone trusted ADR row/material generator for Experiment D")
    ap.add_argument("--scope", choices=("en", "all"), default="en")
    ap.add_argument("--max-files", type=int, default=None)
    ap.add_argument(
        "--lab-root",
        default=None,
        metavar="PATH",
        help="Lab directory (folder that will contain research/). Relative paths resolve from "
        "the current working directory, e.g. ../trusted-adr-lab when run from scripts/. "
        "Writes to <lab-root>/research/... instead of BTC/research/. Default: legacy BTC research/.",
    )
    args = ap.parse_args()

    _LAB_ROOT = resolve_lab_root_arg(args.lab_root)
    if _LAB_ROOT is not None and not _LAB_ROOT.is_dir():
        _LAB_ROOT.mkdir(parents=True, exist_ok=True)

    trusted = paths()
    write_readme()
    records = collect_records(args.scope, args.max_files)
    fact_rows = build_fact_manifest(records)
    conflicts, benign, ambiguity = build_row_sets(records)
    audits = audit_sample(conflicts, benign, ambiguity)

    write_jsonl(trusted["corpus_manifest"], [{"source_family": SOURCE_FAMILY, "source_repo": SOURCE_REPO, "source_repo_url": SOURCE_REPO_URL, "source_url": source_url(r["source_path"]), "source_corpus_type": SOURCE_CORPUS_TYPE, "source_path": r["source_path"], "source_commit": r["source_commit"], "title": r["title"], "provenance_level": "doc_exact", "review_status": "unreviewed"} for r in records])
    write_jsonl(trusted["fact_manifest"], fact_rows)
    write_jsonl(trusted["conflicts"], conflicts)
    write_jsonl(trusted["benign"], benign)
    write_jsonl(trusted["ambiguity"], ambiguity)
    write_jsonl(trusted["audit"], audits)
    write_source_links(conflicts, benign, ambiguity)
    write_reports(records, fact_rows, conflicts, benign, ambiguity, audits)

    checkpoint("trusted_adr_materialized", f"Generated standalone trusted ADR artifacts from {len(records)} markdown files", files=len(records), fact_rows=len(fact_rows), conflict_rows=len(conflicts), benign_rows=len(benign), ambiguity_rows=len(ambiguity), audit_rows=len(audits))
    log_event("trusted_adr_materialized", files=len(records), fact_rows=len(fact_rows), conflict_rows=len(conflicts), benign_rows=len(benign), ambiguity_rows=len(ambiguity), audit_rows=len(audits), scope=args.scope, max_files=args.max_files)
    print(f"Trusted ADR artifacts written to {trusted_dir()}")


if __name__ == "__main__":
    main()
