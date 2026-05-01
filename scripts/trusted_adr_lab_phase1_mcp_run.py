#!/usr/bin/env python3
"""Trusted ADR Lab — Phase 1 (corpus import) via Spirl MCP.

Thin wrapper around ``trusted_adr_lab_mcp_pipeline.run_phase1``.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from trusted_adr_lab_mcp_pipeline import run_phase1


def main() -> int:
    ap = argparse.ArgumentParser(description="Trusted ADR Lab Phase 1 via Spirl MCP.")
    ap.add_argument(
        "--resume",
        action="store_true",
        help="Keep existing TAL log/checkpoints; only import ADR facts that "
        "are not already present in the project.",
    )
    args = ap.parse_args()
    return run_phase1(resume=bool(args.resume))


if __name__ == "__main__":
    raise SystemExit(main())
