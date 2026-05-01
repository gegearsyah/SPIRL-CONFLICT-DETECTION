#!/usr/bin/env python3
"""Count data rows in Real Data Lab markdown tables (list_conflict.md, list_benign.md)."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


def count_table_rows(md_path: Path) -> tuple[int, list[str]]:
    text = md_path.read_text(encoding="utf-8")
    ids: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        if re.match(r"^\|\s*[-]{2,}", line):  # separator
            continue
        if "ID" in line and "Based On" in line:  # header
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 3:
            continue
        row_id = parts[1]
        if row_id and not row_id.startswith("-"):
            ids.append(row_id)
    return len(ids), ids


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--btc-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Beyond Temporal Contradiction directory",
    )
    args = p.parse_args()
    root: Path = args.btc_root
    conflict = root / "real-data-lab" / "list_conflict.md"
    benign = root / "real-data-lab" / "list_benign.md"
    for label, path in (("conflict", conflict), ("benign", benign)):
        if not path.is_file():
            print(f"{label}: MISSING {path}")
            continue
        n, ids = count_table_rows(path)
        print(f"{label}: {n} rows ({path.name})")
        if ids:
            print(f"  first: {ids[0]}  last: {ids[-1]}")
    if conflict.is_file() and benign.is_file():
        nc, _ = count_table_rows(conflict)
        nb, _ = count_table_rows(benign)
        print(f"combined: {nc + nb} rows")


if __name__ == "__main__":
    main()
