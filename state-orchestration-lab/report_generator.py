#!/usr/bin/env python3
"""
Report generator — outputs LaTeX table, CSV, and JSON for the ablation sweep.

Writes to results/ablation_sweep_*.{tex,csv,json} in the state-orchestration-lab directory.
"""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from ablation_runner import ConfigResult

_LAB_DIR = Path(__file__).resolve().parent
_RESULTS_DIR = _LAB_DIR / "results"


def _ensure_results_dir() -> Path:
    _RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    return _RESULTS_DIR


def generate_latex_table(results: list[ConfigResult], *, path: Path | None = None) -> str:
    """Generate a LaTeX table ready for the NeurIPS paper."""
    lines = [
        r"\begin{table}[t]",
        r"\centering",
        r"\caption{Offline ablation on the Real Data Lab semantic slice (40 contradiction proposals, 26 benign controls; "
        r"79-fact SKF baseline; MiniLM retrieval). Each column runs the \textbf{hybrid cascade lab} "
        r"(v2.0-hybrid-resplit shape: Stages 1--5 in cost order, temporal-only \texttt{prune\_set}, plane arbitration, "
        r"Stage~5 = progressive NLI pipeline without live LLM judge). Configs A$\to$E stack defenses; F--G swap NLI encoder. "
        r"SparseCL rerank when installed; \textbf{E-Ver.}\ = Hoyer pre-filter only.}",
        r"\label{tab:semantic_ablation}",
        r"\small",
        r"\begin{tabular}{l c c c c c c c c}",
        r"\toprule",
        r"\textbf{Config} & \textbf{Bidir} & \textbf{Margin} & \textbf{E-Ver.} & "
        r"\textbf{TP} & \textbf{FP} & \textbf{FN} & \textbf{Precision} & \textbf{F1} \\",
        r"\midrule",
    ]

    for r in results:
        s = r.to_summary_dict()
        bidir = r"\checkmark" if s["bidirectional"] else "--"
        margin = f"{s['margin']:.2f}" if s["margin"] > 0 else "--"
        everify = s.get("sparsecl_everify", s.get("sparsecl", False))
        sparsecl = r"\checkmark" if everify else "--"
        precision = f"{s['precision']:.3f}"
        f1 = f"{s['f1']:.3f}"

        # Bold best F1 row
        is_best_f1 = s["f1"] == max(rr.f1 for rr in results)
        if is_best_f1:
            precision = r"\textbf{" + precision + "}"
            f1 = r"\textbf{" + f1 + "}"

        model_note = ""
        if "wanli" in r.config.name.lower():
            model_note = r"$^\dagger$"

        lines.append(
            f"  {r.config.short_label()}{model_note} & {bidir} & {margin} & {sparsecl} & "
            f"{s['TP']} & {s['FP']} & {s['FN']} & {precision} & {f1} \\\\"
        )

    lines.extend([
        r"\bottomrule",
        r"\end{tabular}",
        r"\vspace{2pt}",
        r"{\footnotesize $^\dagger$ DeBERTa-v3-large-mnli-fever-anli-ling-wanli}",
        r"\end{table}",
    ])

    tex = "\n".join(lines)

    if path:
        path.write_text(tex, encoding="utf-8")
    else:
        out = _ensure_results_dir() / "ablation_sweep_summary.tex"
        out.write_text(tex, encoding="utf-8")
        path = out

    return tex


def generate_csv(results: list[ConfigResult], *, path: Path | None = None) -> Path:
    """Generate a CSV with per-config summary metrics."""
    out = path or (_ensure_results_dir() / "ablation_sweep_summary.csv")

    rows = [r.to_summary_dict() for r in results]
    if not rows:
        out.write_text("", encoding="utf-8")
        return out

    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    return out


def generate_detailed_csv(results: list[ConfigResult], *, path: Path | None = None) -> Path:
    """Generate a per-proposal CSV with full detail."""
    out = path or (_ensure_results_dir() / "ablation_sweep_detailed.csv")

    fieldnames = [
        "config", "proposal_id", "proposal_key", "ground_truth",
        "predicted", "detected", "latency_ms", "neighbor_count",
    ]

    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in results:
            for p in r.proposals:
                w.writerow({
                    "config": p.config_name,
                    "proposal_id": p.proposal_id,
                    "proposal_key": p.proposal_key,
                    "ground_truth": p.ground_truth,
                    "predicted": p.predicted,
                    "detected": p.detected,
                    "latency_ms": round(p.latency_ms, 1),
                    "neighbor_count": p.neighbor_count,
                })

    return out


def generate_json(results: list[ConfigResult], *, path: Path | None = None) -> Path:
    """Generate a JSON summary."""
    out = path or (_ensure_results_dir() / "ablation_sweep_summary.json")

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "configs": [r.to_summary_dict() for r in results],
        "false_positives": {},
    }

    # Per-config false positive details
    for r in results:
        fp_list = [
            {
                "proposal_key": p.proposal_key,
                "proposal_body": p.proposal_body,
                "neighbor_count": p.neighbor_count,
            }
            for p in r.proposals
            if p.ground_truth == "benign" and p.detected
        ]
        if fp_list:
            payload["false_positives"][r.config.name] = fp_list

    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return out


def generate_all(results: list[ConfigResult]) -> dict[str, Path]:
    """Generate all report formats."""
    _ensure_results_dir()

    tex_path = _RESULTS_DIR / "ablation_sweep_summary.tex"
    csv_path = _RESULTS_DIR / "ablation_sweep_summary.csv"
    detail_path = _RESULTS_DIR / "ablation_sweep_detailed.csv"
    json_path = _RESULTS_DIR / "ablation_sweep_summary.json"

    generate_latex_table(results, path=tex_path)
    generate_csv(results, path=csv_path)
    generate_detailed_csv(results, path=detail_path)
    generate_json(results, path=json_path)

    return {
        "tex": tex_path,
        "csv": csv_path,
        "detailed_csv": detail_path,
        "json": json_path,
    }
