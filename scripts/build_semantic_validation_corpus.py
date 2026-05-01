#!/usr/bin/env python3
"""
Regenerate real-data-lab slices for semantic-contradiction-only validation:

1. list_conflict_semantic_only.md — already hand-synced from list_conflict.md;
   this script can verify row count (40) when --check is passed.
2. list_benign_semantic_focus.md — benign rows that stress the semantic path:
   - all paraphrase rows (b-par-*), and
   - any row whose Based On overlaps a baseline fact referenced by c-sem-*.

Proposed fact keys are rewritten to p-sben-NN and row IDs to sb-* so injections
do not collide with a prior full list_benign.md run on the same project.

Usage:
  python build_semantic_validation_corpus.py [--write]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
BTC = _SCRIPTS.parent
RDL = BTC / "real-data-lab"

_SEM_ROW = re.compile(
    r"^\|\s*(c-sem-\d+)\s*\|\s*([^|]+)\|",
    re.I | re.M,
)
_BENIGN_ROW = re.compile(
    r"^\|\s*(b-[a-z]+-\d+)\s*\|\s*([^|]+)\|\s*(.+?)\s*\|\s*([^|]+)\|\s*(.+?)\s*\|\s*([^|]*?)\s*\|\s*$",
    re.I,
)
_KEY_RE = re.compile(r"\*\*Key:\*\*\s*(\S+)", re.I)


def semantic_baseline_keys(semantic_md: str) -> set[str]:
    keys: set[str] = set()
    for m in _SEM_ROW.finditer(semantic_md):
        col = m.group(2).strip()
        for part in col.split(","):
            k = part.strip()
            if k.startswith("f-"):
                keys.add(k)
    return keys


def parse_benign_lines(text: str) -> list[tuple[str, str]]:
    """Return list of (full_line, row_id) for data rows."""
    out: list[tuple[str, str]] = []
    for line in text.splitlines():
        line_st = line.strip()
        if not line_st.startswith("| b-"):
            continue
        m = _BENIGN_ROW.match(line_st)
        if m:
            out.append((line_st, m.group(1).strip().lower()))
    return out


def rewrite_benign_line(line: str, new_id: str, new_key: str) -> str:
    """Replace leading ID and **Key:** token in the markdown row."""
    s = line.strip()
    s = re.sub(r"^\|\s*b-[a-z]+-\d+\s*", f"| {new_id} ", s)
    s = _KEY_RE.sub(f"**Key:** {new_key} ", s, count=1)
    return s


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="Write list_benign_semantic_focus.md")
    ap.add_argument("--check", action="store_true", help="Verify semantic-only file has 40 c-sem rows")
    args = ap.parse_args()

    sem_path = RDL / "list_conflict_semantic_only.md"
    if not sem_path.is_file():
        print(f"Missing {sem_path}", file=sys.stderr)
        return 1
    sem_body = sem_path.read_text(encoding="utf-8")
    sem_rows = len(re.findall(r"^\|\s*c-sem-\d+\s*\|", sem_body, re.M))
    if args.check:
        print(f"list_conflict_semantic_only.md: {sem_rows} c-sem rows (expected 40)")
        return 0 if sem_rows == 40 else 1

    sem_keys = semantic_baseline_keys(sem_body)
    benign_path = RDL / "list_benign.md"
    benign_text = benign_path.read_text(encoding="utf-8")
    rows = parse_benign_lines(benign_text)

    selected: list[tuple[str, str]] = []
    for line, rid in rows:
        if rid.startswith("b-par-"):
            selected.append((line, rid))
            continue
        m = _BENIGN_ROW.match(line.strip())
        if not m:
            continue
        based = [x.strip() for x in m.group(2).split(",") if x.strip()]
        if any(b in sem_keys for b in based):
            selected.append((line, rid))

    dedup: dict[str, tuple[str, str]] = {}
    for line, rid in selected:
        dedup[rid] = (line, rid)
    ordered = list(dedup.values())
    ordered.sort(key=lambda x: x[1])

    header = (
        "## Benign proposals — semantic validation focus\n\n"
        "Documentation-consistent proposals for **false-positive** checks on the **semantic "
        "contradiction** path (paraphrase + overlap with `c-sem-*` baseline facts). "
        "Run after `real_data_lab_semantic_conflict_mcp_run.py` on the same Spirl project.\n\n"
        "**IDs** use `sb-*` and proposed keys `p-sben-*` so this batch does not collide with "
        "a prior full `list_benign.md` run (`p-ben-*`).\n\n"
        "| ID        | Based On Fact | Proposed Fact Details (Key / Category / Value / Valid From-Until) "
        "| Expected Labels | Rationale & Realism | Source Support |\n"
        "| --------- | ------------- | "
        "--------------------------------------------------------------------------------------------------------------------------------------------------------------------- "
        "| --------------- | ---------------------------------------------------------------------------------------- | -------------- |\n"
    )

    lines_out = [header.rstrip() + "\n"]
    for i, (line, rid) in enumerate(ordered, start=1):
        suffix = rid.removeprefix("b-")
        new_id = f"sb-{suffix}"
        new_key = f"p-sben-{i:02d}"
        lines_out.append(rewrite_benign_line(line, new_id, new_key) + "\n")

    out_path = RDL / "list_benign_semantic_focus.md"
    if args.write:
        out_path.write_text("".join(lines_out), encoding="utf-8")
        print(f"Wrote {len(ordered)} rows to {out_path}")
    else:
        print(f"Would write {len(ordered)} rows to {out_path} (pass --write)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
