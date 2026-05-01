#!/usr/bin/env python3
"""
Exclusive lock for Real Data Lab scripts that append to real_data_lab_execution_log.jsonl.

Only one of phase1 / phase2 / benign / phase3 may run at a time. Concurrent runs interleave JSONL
lines and mix project_ids (looks like “Phase 1 and Phase 2 together” in one file).
"""
from __future__ import annotations

import sys
from contextlib import contextmanager, suppress
from pathlib import Path
from typing import Any, Iterator

from paper3_paths import btc_root


def rdl_pipeline_lock_path() -> Path:
    return btc_root() / "real-data-lab" / "research" / "real_data_lab_pipeline.lock"


def acquire_rdl_pipeline_lock(*, ignore: bool = False) -> Any:
    if ignore:
        return None
    path = rdl_pipeline_lock_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    fp = open(path, "a+b")
    try:
        if sys.platform == "win32":
            import msvcrt

            fp.seek(0)
            msvcrt.locking(fp.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(fp.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError as e:
        fp.close()
        raise SystemExit(
            "Another Real Data Lab script is running (phase1, phase2, benign, or phase3), or a stale "
            f"{path.name} remains after a crash. Only one may run at a time — they share "
            "real_data_lab_execution_log.jsonl. Stop the other process, or pass "
            "--ignore-pipeline-lock (or Phase 2: --ignore-phase2-lock) if you are sure nothing else "
            f"is writing. Original error: {e}",
        ) from e
    return fp


def release_rdl_pipeline_lock(fp: Any) -> None:
    if fp is None:
        return
    try:
        if sys.platform == "win32":
            import msvcrt

            fp.seek(0)
            with suppress(OSError):
                msvcrt.locking(fp.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            with suppress(OSError):
                fcntl.flock(fp.fileno(), fcntl.LOCK_UN)
    finally:
        fp.close()


@contextmanager
def rdl_pipeline_lock(*, ignore: bool = False) -> Iterator[None]:
    fp = acquire_rdl_pipeline_lock(ignore=ignore)
    try:
        yield
    finally:
        release_rdl_pipeline_lock(fp)
