#!/usr/bin/env python3
"""
Repair Gemini-exported SKF JSON (common issues: facts opened with {, truncated references, edges/episodes stubs).

Usage:
  python repair_real_data_lab_skf.py [--write]

Default: validate repair and print summary. With --write: overwrite the .skf.json in real-data-lab.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

DEFAULT_SKF = (
    Path(__file__).resolve().parent.parent
    / "real-data-lab"
    / "Project Core Platform.skf.json"
)


def repair_skf_text(raw: str) -> str:
    s = raw.replace('"facts":{', '"facts":[', 1)
    # Drop first bogus array element (metadata tail without key/value)
    s = re.sub(
        r"\n\s*\{\s*"
        r'"metadata":\s*\{[^}]+\},\s*'
        r'"valid_from":\s*"[^"]*",\s*'
        r'"valid_until":\s*null\s*'
        r"\},?\s*",
        "\n",
        s,
        count=1,
    )
    s = re.sub(r'"references":\s*,', '"references": []', s)
    s = s.replace('"edges":,', '"edges": [],', 1)
    s = s.replace(
        '"episodes":,\n        "metadata":',
        '"episodes": [\n      {\n        "id": "e-extract-01",\n        '
        '"type": "extraction",\n        '
        '"summary": "TechDocs / public docs extraction (episode header recovered from partial export).",\n        '
        '"timestamp": "2026-04-02T10:44:00Z",\n        "targets": [],\n        "metadata":',
        1,
    )
    return s


def references_for_mcp(refs: object) -> list[str]:
    """SPIRL import_skf expects references: list[str]."""
    if refs is None:
        return []
    if isinstance(refs, list):
        out: list[str] = []
        for item in refs:
            if isinstance(item, str):
                out.append(item)
            elif isinstance(item, dict):
                t = item.get("title") or ""
                u = item.get("url") or ""
                out.append(f"{t}: {u}".strip(": ").strip() if (t or u) else json.dumps(item))
            else:
                out.append(str(item))
        return out
    return [str(refs)]


def facts_for_import_skf(doc: dict) -> list[dict]:
    facts_in = doc.get("facts") or []
    out: list[dict] = []
    for f in facts_in:
        if not isinstance(f, dict):
            continue
        key = f.get("key")
        val = f.get("value")
        if not key or val is None:
            continue
        row = {
            "key": str(key),
            "value": str(val),
            "layer": str(f.get("layer") or "product"),
            "category": str(f.get("category") or "other"),
            "confidence": float(f.get("confidence", 0.8)),
            "references": references_for_mcp(f.get("references")),
            "metadata": f.get("metadata") if isinstance(f.get("metadata"), dict) else {},
            "valid_from": f.get("valid_from"),
            "valid_until": f.get("valid_until"),
        }
        out.append(row)
    return out


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--path", type=Path, default=DEFAULT_SKF, help="Path to SKF JSON")
    p.add_argument("--write", action="store_true", help="Write repaired JSON back to --path")
    args = p.parse_args()
    path: Path = args.path
    if not path.is_file():
        print(f"Missing file: {path}", file=sys.stderr)
        return 1
    raw = path.read_text(encoding="utf-8")
    repaired = repair_skf_text(raw)
    try:
        doc = json.loads(repaired)
    except json.JSONDecodeError as e:
        print("JSON still invalid after repair:", e, file=sys.stderr)
        print(repaired[max(0, e.pos - 80) : e.pos + 80], file=sys.stderr)
        return 1
    facts = doc.get("facts") or []
    print(f"OK: {len(facts)} facts, edges={len(doc.get('edges') or [])}, episodes={len(doc.get('episodes') or [])}")
    if args.write:
        path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
