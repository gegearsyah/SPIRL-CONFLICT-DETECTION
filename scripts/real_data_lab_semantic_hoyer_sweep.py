#!/usr/bin/env python3
"""
Run the semantic validation MCP pipeline for a list of Hoyer coefficients (default: 0.10, 0.15, 0.25 — 0.20 omitted after poor lab results).

Each value gets isolated artifacts:
  real_data_lab_semantic_execution_log.hoyer_0p10.jsonl
  real_data_lab_semantic_checkpoints.hoyer_0p10.jsonl
  …

Operator responsibility: set the matching Hoyer λ on the Spirl backend (or use a dedicated project /
config per run) **before** each iteration. This script only tags logs and filenames; it does not
change server configuration.

Usage:
  python real_data_lab_semantic_hoyer_sweep.py              # run all four
  python real_data_lab_semantic_hoyer_sweep.py --dry-run  # print commands only
  python real_data_lab_semantic_hoyer_sweep.py --hoyers 0.1 0.25
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
DEFAULT_HOYERS = (0.10, 0.15, 0.25)


def main() -> int:
    ap = argparse.ArgumentParser(description="Sequential semantic validation runs for Hoyer sweep")
    ap.add_argument(
        "--hoyers",
        type=float,
        nargs="*",
        default=list(DEFAULT_HOYERS),
        metavar="LAMBDA",
        help=f"Hoyer values (default: {' '.join(str(x) for x in DEFAULT_HOYERS)})",
    )
    ap.add_argument("--dry-run", action="store_true", help="Print subprocess commands only")
    ap.add_argument("--skip-benign", action="store_true", help="Only run conflict injections")
    ap.add_argument("--conflict-args", default="", help="Extra args passed to conflict script (quoted string)")
    ap.add_argument("--benign-args", default="", help="Extra args passed to benign script (quoted string)")
    args = ap.parse_args()

    conflict_py = _SCRIPTS / "real_data_lab_semantic_conflict_mcp_run.py"
    benign_py = _SCRIPTS / "real_data_lab_semantic_benign_mcp_run.py"

    for h in args.hoyers:
        hoyer = float(h)
        c_cmd = [sys.executable, str(conflict_py), "--hoyer", str(hoyer)]
        b_cmd = [sys.executable, str(benign_py), "--hoyer", str(hoyer)]
        if args.conflict_args.strip():
            c_cmd.extend(args.conflict_args.split())
        if args.benign_args.strip():
            b_cmd.extend(args.benign_args.split())

        print(f"\n=== Hoyer lambda = {hoyer} (experiment id from --hoyer) ===", flush=True)
        print("Conflict:", " ".join(c_cmd), flush=True)
        if not args.dry_run:
            subprocess.run(c_cmd, cwd=str(_SCRIPTS), check=True)

        if not args.skip_benign:
            print("Benign: ", " ".join(b_cmd), flush=True)
            if not args.dry_run:
                subprocess.run(b_cmd, cwd=str(_SCRIPTS), check=True)

        if not args.dry_run:
            print(
                f"Done lambda={hoyer}. Before the next iteration: apply the next Hoyer value on Spirl "
                "or switch to a clean project if you need fresh p-* / p-sben-* keys.",
                flush=True,
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
