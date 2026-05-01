#!/usr/bin/env python3
"""Trusted ADR Lab — Phase 2 (typed + ambiguity injections) via Spirl MCP.

Injects the 8 typed conflict rows (4 semantic + 2 constraint + 2 temporal)
and the 4 ambiguity rows from
``trusted-adr-lab/research/trusted_adr/`` into the TAL project and logs
the full preflight/async envelope for later scoring by
``trusted_adr_lab_phase3_mcp_run.py``.

Thin wrapper around ``trusted_adr_lab_mcp_pipeline.run_phase2``.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from trusted_adr_lab_mcp_pipeline import run_phase2


def main() -> int:
    ap = argparse.ArgumentParser(description="Trusted ADR Lab Phase 2 via Spirl MCP.")
    ap.add_argument(
        "--resume",
        action="store_true",
        help="Keep existing TAL log/checkpoints across re-runs.",
    )
    args = ap.parse_args()
    return run_phase2(resume=bool(args.resume))


if __name__ == "__main__":
    raise SystemExit(main())
