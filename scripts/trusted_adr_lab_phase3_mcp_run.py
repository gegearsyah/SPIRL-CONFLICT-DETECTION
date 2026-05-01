#!/usr/bin/env python3
"""Trusted ADR Lab — Phase 3 (scoring + reporting).

Reads ``trusted_adr_lab_execution_log.jsonl`` and writes:
  * ``trusted_adr_lab_mixed_report.md`` — main EMNLP-facing metrics table
    (pooled precision/recall, core-N exact-type recall, benign FP rate,
    Wave 4.3 governance section).
  * ``trusted_adr_lab_confusion_matrix.md`` — per-class confusion matrix.
  * ``trusted_adr_lab_phase3_report.md`` — checkpoint summary.
  * ``paper3_phase3_report.experiment_D.md`` — legacy-path companion
    report for the paper appendix.

Thin wrapper around ``trusted_adr_lab_mcp_pipeline.run_phase3``.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from trusted_adr_lab_mcp_pipeline import run_phase3


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Trusted ADR Lab Phase 3 — scoring + report generation."
    )
    ap.parse_args()
    return run_phase3()


if __name__ == "__main__":
    raise SystemExit(main())
