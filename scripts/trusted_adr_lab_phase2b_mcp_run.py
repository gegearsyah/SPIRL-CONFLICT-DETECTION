#!/usr/bin/env python3
"""Trusted ADR Lab — Phase 2b (benign injections) via Spirl MCP.

Injects the 6 benign TAL rows and logs the full preflight envelope, so
``trusted_adr_lab_phase3_mcp_run.py`` can compute benign FP and
`needs_review` FP counters without re-calling the server.

Thin wrapper around ``trusted_adr_lab_mcp_pipeline.run_phase2b``.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from trusted_adr_lab_mcp_pipeline import run_phase2b


def main() -> int:
    ap = argparse.ArgumentParser(description="Trusted ADR Lab Phase 2b (benign) via Spirl MCP.")
    ap.add_argument(
        "--resume",
        action="store_true",
        help="Keep existing TAL log/checkpoints across re-runs.",
    )
    args = ap.parse_args()
    return run_phase2b(resume=bool(args.resume))


if __name__ == "__main__":
    raise SystemExit(main())
