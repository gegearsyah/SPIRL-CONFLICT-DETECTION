#!/usr/bin/env python3
"""Wait for Real Data Lab Phase 1 checkpoint, then run Phase 2 + Phase 2b (corpus paths from .spirl/config.json)."""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
_CHECKPOINTS = _SCRIPTS.parent / "real-data-lab" / "research" / "real_data_lab_checkpoints.jsonl"


def phase1_done() -> bool:
    if not _CHECKPOINTS.exists():
        return False
    for line in _CHECKPOINTS.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            o = json.loads(line)
        except json.JSONDecodeError:
            continue
        if (
            o.get("phase") == 1
            and o.get("checkpoint_type") == "phase_complete"
            and o.get("status") == "complete"
        ):
            return True
    return False


def main() -> int:
    poll_s = 20
    max_wait_s = 7200
    elapsed = 0
    while elapsed < max_wait_s:
        if phase1_done():
            print("Phase 1 complete; starting Phase 2...", flush=True)
            r = subprocess.run(
                [sys.executable, str(_SCRIPTS / "real_data_lab_phase2_mcp_run.py")],
                cwd=str(_SCRIPTS),
            )
            if r.returncode != 0:
                return r.returncode
            print("Starting Phase 2b...", flush=True)
            r = subprocess.run(
                [sys.executable, str(_SCRIPTS / "real_data_lab_benign_mcp_run.py")],
                cwd=str(_SCRIPTS),
            )
            return r.returncode
        time.sleep(poll_s)
        elapsed += poll_s
        if elapsed % 120 == 0:
            print(f"Waiting for Phase 1 phase_complete... ({elapsed // 60} min)", flush=True)
    print("Timeout waiting for Phase 1.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
