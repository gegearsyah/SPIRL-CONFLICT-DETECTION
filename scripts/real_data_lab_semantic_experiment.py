"""
Shared paths + metadata for semantic validation runs (e.g. Hoyer λ sweeps: 0.10, 0.15, 0.25).

Each experiment id gets its own execution log, checkpoints, and reports so multiple backend
configurations can be compared without overwriting artifacts.

CLI flags override `.spirl/config.json` keys `real_data_lab_semantic_experiment` and
`real_data_lab_semantic_hoyer_lambda`.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SemanticTrackPaths:
    """Filesystem targets for one semantic validation experiment."""

    experiment_id: str
    execution_log: Path
    checkpoints: Path
    conflict_report: Path
    validation_report: Path


def sanitize_experiment_id(raw: str) -> str:
    s = raw.strip().lower().replace(" ", "_")
    s = re.sub(r"[^a-z0-9._-]+", "", s)
    s = s.replace(".", "p")
    return s or "default"


def hoyer_experiment_id(hoyer: float) -> str:
    """Stable id from λ, e.g. 0.10 → hoyer_0p10 (two decimal places)."""
    return "hoyer_" + f"{hoyer:.2f}".replace(".", "p")


def _config_experiment_block(cfg: dict[str, Any]) -> dict[str, Any]:
    block = cfg.get("real_data_lab_semantic_experiment")
    return dict(block) if isinstance(block, dict) else {}


def resolve_semantic_track(
    research_dir: Path,
    cfg: dict[str, Any],
    *,
    experiment_id_cli: str | None,
    hoyer_lambda_cli: float | None,
) -> tuple[SemanticTrackPaths, dict[str, Any]]:
    """
    Resolve log/report paths and the JSON object to attach as `experiment` on each log line.

    Returns (paths, experiment_envelope) where experiment_envelope is e.g.
    {"id": "hoyer_0p15", "hoyer_lambda": 0.15}.
    """
    cfg_block = _config_experiment_block(cfg)
    meta: dict[str, Any] = {k: v for k, v in cfg_block.items() if k != "id"}

    eid = (experiment_id_cli or "").strip()
    if not eid:
        eid = (cfg_block.get("id") or "").strip()

    cfg_hoyer = cfg.get("real_data_lab_semantic_hoyer_lambda")
    hoyer: float | None = hoyer_lambda_cli
    if hoyer is None and cfg_hoyer is not None:
        try:
            hoyer = float(cfg_hoyer)
        except (TypeError, ValueError):
            hoyer = None

    if hoyer is not None:
        meta["hoyer_lambda"] = float(hoyer)
        if not eid:
            eid = hoyer_experiment_id(float(hoyer))

    if not eid or sanitize_experiment_id(eid) == "default":
        sid = "default"
        return (
            SemanticTrackPaths(
                experiment_id=sid,
                execution_log=research_dir / "real_data_lab_semantic_execution_log.jsonl",
                checkpoints=research_dir / "real_data_lab_semantic_checkpoints.jsonl",
                conflict_report=research_dir / "real_data_lab_semantic_conflict_report.md",
                validation_report=research_dir / "real_data_lab_semantic_validation_report.md",
            ),
            {"id": sid, **{k: v for k, v in meta.items() if k != "id"}},
        )

    sid = sanitize_experiment_id(eid)
    suffix = f".{sid}"
    return (
        SemanticTrackPaths(
            experiment_id=sid,
            execution_log=research_dir / f"real_data_lab_semantic_execution_log{suffix}.jsonl",
            checkpoints=research_dir / f"real_data_lab_semantic_checkpoints{suffix}.jsonl",
            conflict_report=research_dir / f"real_data_lab_semantic_conflict_report{suffix}.md",
            validation_report=research_dir / f"real_data_lab_semantic_validation_report{suffix}.md",
        ),
        {"id": sid, **{k: v for k, v in meta.items() if k != "id"}},
    )


def tag_log_row(experiment: dict[str, Any], row: dict[str, Any]) -> dict[str, Any]:
    out = dict(row)
    out["experiment"] = dict(experiment)
    return out


def add_semantic_experiment_cli(ap: Any) -> None:
    """Register --experiment-id and --hoyer on an ArgumentParser."""
    g = ap.add_argument_group("experiment / sweep (reuse for multiple Hoyer values)")
    g.add_argument(
        "--experiment-id",
        default="",
        metavar="ID",
        help="Stable id for log filenames (default: from --hoyer or real_data_lab_semantic_experiment.id in config)",
    )
    g.add_argument(
        "--hoyer",
        type=float,
        default=None,
        dest="hoyer_lambda",
        metavar="LAMBDA",
        help="Hoyer coefficient used on the Spirl side; tags JSONL and sets default id hoyer_0pXX",
    )
