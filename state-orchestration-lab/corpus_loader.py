#!/usr/bin/env python3
"""
Corpus loader for the ablation harness.

Reads:
  - ../real-data-lab/Project Core Platform.skf.json  → baseline facts
  - ../real-data-lab/list_conflict_semantic_only.md   → conflict proposals  (label=conflict)
  - ../real-data-lab/list_benign_semantic_focus.md     → benign proposals    (label=benign)

Returns structured dicts ready for the ablation runner.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

_LAB_DIR = Path(__file__).resolve().parent
_DATA_DIR = _LAB_DIR.parent / "real-data-lab"

_SKF_FILE = _DATA_DIR / "Project Core Platform.skf.json"
_CONFLICT_FILE = _DATA_DIR / "list_conflict_semantic_only.md"
_BENIGN_FILE = _DATA_DIR / "list_benign_semantic_focus.md"


# ── SKF baseline facts ──────────────────────────────────────────────────────

def load_baseline_facts(path: Path | None = None) -> list[dict[str, Any]]:
    """Load baseline facts from the SKF JSON corpus."""
    skf_path = path or _SKF_FILE
    if not skf_path.is_file():
        raise FileNotFoundError(f"SKF corpus not found: {skf_path}")

    raw = json.loads(skf_path.read_text(encoding="utf-8"))
    facts: list[dict[str, Any]] = []
    for fact in raw.get("facts", []):
        key = fact.get("key", "")
        body = (fact.get("value") or "").strip()
        if not key or not body:
            continue
        facts.append({
            "key": key,
            "body": body,
            "layer": fact.get("layer"),
            "category": fact.get("category"),
            "kind": fact.get("category"),  # for pipeline compatibility
        })
    return facts


# ── Markdown proposal parsers ────────────────────────────────────────────────

def _parse_md_table(path: Path) -> list[dict[str, str]]:
    """Parse the rich markdown table format used in real-data-lab lists.

    Format: | c-sem-01 | f-api-15 | **Key:** p-api-01 **Cat:** apiendpoint **Val:** "..." **Valid:** ... | labels | ... |
    Extracts: id, based_on, key (from **Key:**), body (from **Val:**).
    """
    if not path.is_file():
        raise FileNotFoundError(f"Markdown list not found: {path}")

    text = path.read_text(encoding="utf-8")
    rows: list[dict[str, str]] = []

    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.split("|")]
        # Remove empty leading/trailing from split
        cells = [c for c in cells if c]
        if len(cells) < 3:
            continue

        row_id = cells[0].strip()
        # Skip header / separator rows
        if "---" in row_id or row_id.lower() in ("id", ""):
            continue

        based_on = cells[1].strip() if len(cells) > 1 else ""
        detail_cell = cells[2] if len(cells) > 2 else ""

        # Skip header rows by content
        if "Proposed Fact" in detail_cell or "---" in detail_cell:
            continue

        # Extract key from **Key:** pattern
        key_match = re.search(r"\*\*Key:\*\*\s*(\S+)", detail_cell)
        key = key_match.group(1) if key_match else ""

        # Extract body from **Val:** pattern — everything between **Val:** and **Valid:** (or end)
        val_match = re.search(
            r'\*\*Val:\*\*\s*["\u201c]?(.*?)["\u201d]?\s*(?:\*\*Valid:\*\*|$)',
            detail_cell,
            re.DOTALL,
        )
        body = val_match.group(1).strip().strip('"').strip('\u201c\u201d') if val_match else ""

        if not key and not body:
            continue

        rows.append({
            "id": row_id,
            "key": key,
            "body": body,
            "based_on": based_on,
        })

    return rows


def load_conflict_proposals(path: Path | None = None) -> list[dict[str, Any]]:
    """Load semantic contradiction proposals (ground truth: conflict)."""
    rows = _parse_md_table(path or _CONFLICT_FILE)
    return [
        {
            "key": r["key"],
            "body": r["body"],
            "based_on": r["based_on"],
            "label": "conflict",
            "proposal_id": r["id"],
        }
        for r in rows
    ]


def load_benign_proposals(path: Path | None = None) -> list[dict[str, Any]]:
    """Load benign (non-contradictory) proposals (ground truth: benign)."""
    rows = _parse_md_table(path or _BENIGN_FILE)
    return [
        {
            "key": r["key"],
            "body": r["body"],
            "based_on": r["based_on"],
            "label": "benign",
            "proposal_id": r["id"],
        }
        for r in rows
    ]


def load_all_proposals() -> list[dict[str, Any]]:
    """Load both conflict and benign proposals into a single list."""
    return load_conflict_proposals() + load_benign_proposals()


# ── Summary ──────────────────────────────────────────────────────────────────

def print_corpus_summary() -> None:
    """Print a summary of all loaded data."""
    facts = load_baseline_facts()
    conflicts = load_conflict_proposals()
    benign = load_benign_proposals()
    print(f"Corpus: {len(facts)} baseline facts, {len(conflicts)} conflict proposals, {len(benign)} benign proposals")
    print(f"  SKF: {_SKF_FILE}")
    print(f"  Conflicts: {_CONFLICT_FILE}")
    print(f"  Benign: {_BENIGN_FILE}")

    # Category breakdown
    from collections import Counter
    cats = Counter(f["category"] for f in facts)
    print(f"  Fact categories: {dict(cats)}")


if __name__ == "__main__":
    print_corpus_summary()
