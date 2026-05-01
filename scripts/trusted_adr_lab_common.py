#!/usr/bin/env python3
"""
Trusted ADR Lab (TAL) — shared helpers used by the phase runners.

TAL mirrors the Real Data Lab (RDL) pipeline but on a second corpus
(joelparkerhenderson/architecture-decision-record, 66 public ADR markdown
files).  It exists to give EMNLP reviewers a cross-domain external-
validity signal for the cascade architecture:

  * 8 typed conflict injections covering the 3 applicable core-4
    classes (4 semantic + 2 constraint + 2 temporal; dependency_impact
    is intentionally marked ``n/a`` because plain-text ADRs carry no
    dependency-edge substrate — see Limitations).
  * 4 ambiguity injections that should route to
    ``governance_outcome = needs_review`` (Wave 4.3 / AbstentionBench).
  * 6 benign injections for false-positive accounting.

Rows are pre-materialized by
``experiment_d_trusted_adr_track.py --lab-root ../trusted-adr-lab`` and
live under ``trusted-adr-lab/research/trusted_adr/``.  The TAL phase
runners import those JSONLs and inject them into Spirl via MCP using the
same ``memory_upsert_fact_v1`` transport as RDL.

References:
  * Heng & Soh (arXiv:2505.15008) — Neyman-Pearson selective rejection.
  * AbstentionBench (arXiv:2506.09038) — abstention evaluation protocol.
  * joelparkerhenderson/architecture-decision-record (≈4.6k★).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from paper3_paths import btc_root  # noqa: E402


TAL_SLUG = "trusted_adr_lab"
TAL_AGENT_ID = "tal_phase2_seed_agent"
TAL_PHASE1_AGENT = "tal_phase1_corpus_builder"
TAL_PHASE2B_AGENT = "tal_phase2b_benign_agent"
TAL_PHASE3_AGENT = "tal_phase3_judge_agent"


def tal_root() -> Path:
    return btc_root() / "trusted-adr-lab"


def tal_research_dir() -> Path:
    p = tal_root() / "research"
    p.mkdir(parents=True, exist_ok=True)
    return p


def tal_exec_log() -> Path:
    return tal_research_dir() / "trusted_adr_lab_execution_log.jsonl"


def tal_checkpoints() -> Path:
    return tal_research_dir() / "trusted_adr_lab_checkpoints.jsonl"


def tal_phase1_report() -> Path:
    return tal_research_dir() / "trusted_adr_lab_phase1_report.md"


def tal_phase2_report() -> Path:
    return tal_research_dir() / "trusted_adr_lab_phase2_report.md"


def tal_phase3_report() -> Path:
    return tal_research_dir() / "trusted_adr_lab_phase3_report.md"


def tal_mixed_report() -> Path:
    return tal_research_dir() / "trusted_adr_lab_mixed_report.md"


def tal_confusion_matrix() -> Path:
    return tal_research_dir() / "trusted_adr_lab_confusion_matrix.md"


def tal_trusted_dir() -> Path:
    p = tal_research_dir() / "trusted_adr"
    p.mkdir(parents=True, exist_ok=True)
    return p


def tal_fact_manifest() -> Path:
    return tal_trusted_dir() / "adr_extracted_fact_manifest.jsonl"


def tal_conflict_rows() -> Path:
    return tal_trusted_dir() / "trusted_conflict_rows.jsonl"


def tal_benign_rows() -> Path:
    return tal_trusted_dir() / "trusted_benign_rows.jsonl"


def tal_ambiguity_rows() -> Path:
    return tal_trusted_dir() / "trusted_ambiguity_rows.jsonl"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def tal_expected_counts() -> dict[str, int]:
    """Expected rows per governance bucket for the TAL workload.

    Recorded here (not inferred from disk) so the runners can fail early
    if the materialized JSONLs diverge from the 8 / 4 / 6 contract.
    Keys match the row buckets used in the EMNLP paper.
    """
    return {
        "conflict": 8,  # 4 semantic + 2 constraint + 2 temporal
        "ambiguity": 4,
        "benign": 6,
    }
