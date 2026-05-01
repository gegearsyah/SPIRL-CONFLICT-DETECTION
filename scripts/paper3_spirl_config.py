"""Shared Paper 3 settings from .spirl/config.json."""
from __future__ import annotations

from pathlib import Path
from typing import Any

# Stable p1 → p2 → p3 order (matches research_prompt/paper3_phase1_prompt.md).
PAPER3_PROJECT_KEYS: tuple[str, ...] = (
    "paper3_data_pipeline",
    "paper3_saas",
    "paper3_api_service",
)


def project_order_from_config(cfg: dict[str, Any]) -> list[tuple[str, str]]:
    """Return [(slug, project_uuid), ...] from ``cfg['projects']`` in canonical order."""
    proj = cfg.get("projects")
    if not isinstance(proj, dict):
        raise SystemExit("config.json: missing or invalid 'projects' object")
    out: list[tuple[str, str]] = []
    for key in PAPER3_PROJECT_KEYS:
        if key not in proj:
            raise SystemExit(f"config.json: projects.{key} is required for Paper 3")
        uid = str(proj[key]).strip()
        if not uid:
            raise SystemExit(f"config.json: projects.{key} must be a non-empty UUID string")
        out.append((key, uid))
    return out


def paper3_project_ids(cfg: dict[str, Any]) -> list[str]:
    return [pid for _, pid in project_order_from_config(cfg)]


def paper3_target_per_project(project_ids: list[str], total: int = 200) -> dict[str, int]:
    """Split ``total`` injections across projects; remainder goes to first projects (same as 67/67/66 for n=3)."""
    n = len(project_ids)
    if n == 0:
        return {}
    base, rem = divmod(total, n)
    return {pid: base + (1 if i < rem else 0) for i, pid in enumerate(project_ids)}


def _experiment_token(experiment_id: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in experiment_id)


def paper3_phase2_artifact_paths(root: Path, cfg: dict[str, Any]) -> tuple[Path, Path, Path]:
    """Return (execution_log, checkpoints, phase2_report_md) for this experiment.

    Experiment **A** uses canonical filenames under ``research/``. Any other
    ``paper3_experiment_id`` (e.g. ``B``) uses suffixed files so logs do not mix.
    Phase 1 completion is always read from ``paper3_checkpoints.jsonl`` (see
    ``PHASE1_CHECKPOINTS`` in the Phase 2 driver).
    """
    research = root / "research"
    eid = str(cfg.get("paper3_experiment_id") or "A").strip() or "A"
    if eid.upper() == "A":
        return (
            research / "paper3_execution_log.jsonl",
            research / "paper3_checkpoints.jsonl",
            research / "paper3_phase2_report.md",
        )
    tok = _experiment_token(eid)
    return (
        research / f"paper3_execution_log.experiment_{tok}.jsonl",
        research / f"paper3_checkpoints.experiment_{tok}.jsonl",
        research / f"paper3_phase2_report.experiment_{tok}.md",
    )


def paper3_experiment_block(cfg: dict[str, Any]) -> dict[str, Any | None]:
    """Embed in Phase 2 JSONL rows for cross-architecture comparisons."""
    eid = str(cfg.get("paper3_experiment_id") or "A").strip() or "A"
    arch = str(cfg.get("paper3_architecture_label") or "").strip()
    return {"id": eid, "architecture_label": arch or None}


def paper3_fact_kind(cfg: dict[str, Any]) -> str:
    """Kind for synthetic Paper 3 facts (ground truth, injections, phase1 baselines).

    Must satisfy the DB check constraint facts_kind_check. After adding `research`
    on the server, set paper3_fact_kind to \"research\" in config; otherwise use an
    existing kind such as \"decision\".
    """
    v = cfg.get("paper3_fact_kind")
    if v is not None and str(v).strip():
        return str(v).strip()
    return "decision"
