#!/usr/bin/env python3
"""
Offline grid search for Spiral semantic-stage env vars to reduce benign false positives.

Problem
-------
Benign rows (paraphrases / documentation-consistent text) often look like "contradictions"
to NLI cross-encoders trained on MNLI-style premise–hypothesis pairs. Raising gates
(`NLI_CONTRADICTION_CONFIDENCE_THRESHOLD`, `CONFLICT_EMBEDDING_SIMILARITY_THRESHOLD`,
`SPARSITY_ENTAILMENT_FLOOR`, etc.) trades recall on real contradictions for precision on benigns.

This script replays `list_benign_semantic_focus.md` and optionally `list_conflict_semantic_only.md`
against the **local** `spiral_semantic_stages` pipeline:

1. Load all fact bodies from `Project Core Platform.skf.json`.
2. Embed facts + proposals with **sentence-transformers**, **OpenAI**, or **OpenRouter** (OpenAI-compatible
   `/v1/embeddings`). If `OPENROUTER_API_KEY` is in `spiral_semantic_stages/.env`, the default backend is
   **openrouter** with `OPENROUTER_EMBEDDING_MODEL` (same route as many Spirl deployments).
3. Build Stage-1 candidates via `candidates_from_neighbors` with a low cosine floor, then
   `check_semantic_contradictions_stages(..., settings=cfg)` for each threshold tuple.
4. Optional **`--ablation-sparsecl`**: three passes (no Stage 1.5, rerank-only, E-Verify on) on the same grid.
5. Optional **`--per-row-jsonl`**: after the sweep, dump each row with `trace` (neighbors, SparseCL meta,
   NLI softmax triples, recall-guard flag).
6. Gate / retrieval ablations (same grid): **`--pool-sim-floor`**, **`--nli-predicate-overlap`** (`0` disables
   Stage 1.75), **`--no-nli-bidirectional`**, **`--nli-margin-threshold`** (relax margin gate without
   touching NLI confidence).

Outputs
-------
Prints metrics and optionally writes a recommended `.env`. It does **not** call MCP; for live
Spirl runs you must deploy the same variable values the backend reads (often identical names).

Usage (from repo root or scripts dir)
-------------------------------------
  pip install -r \"../state-orchestration-lab/requirements.txt\" \\
              -r \"../state-orchestration-lab/requirements-spiral-stages.txt\"

  # Spirl-like embeddings + full SparseCL stack + mix report:
  pip install -r \"../state-orchestration-lab/requirements-openai-embed.txt\"
  python semantic_benign_threshold_sweep.py --preset mix --embed-backend openai \\
    --report-md ../real-data-lab/research/semantic_threshold_mix_report.md \\
    --report-csv ../real-data-lab/research/semantic_threshold_mix_report.csv \\
    --per-row-jsonl ../real-data-lab/research/semantic_per_row_trace.jsonl

  # SparseCL ablation (adds `stack` column to CSV/MD):
  python semantic_benign_threshold_sweep.py --preset mix --ablation-sparsecl \\
    --report-md ../real-data-lab/research/semantic_ablation_report.md \\
    --report-csv ../real-data-lab/research/semantic_ablation_report.csv

See also: `real_data_lab_semantic_benign_mcp_run.py` for end-to-end MCP evaluation.
"""
from __future__ import annotations

import argparse
import csv
import itertools
import json
import math
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

_SCRIPTS = Path(__file__).resolve().parent
_BTC = _SCRIPTS.parent
_SOL = _BTC / "state-orchestration-lab"
if str(_SOL) not in sys.path:
    sys.path.insert(0, str(_SOL))
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from kg_orchestrator.models import ExistingFact, FactProposal  # noqa: E402
from real_data_lab_semantic_benign_mcp_run import parse_semantic_benign_table  # noqa: E402
from real_data_lab_phase2_mcp_run import parse_conflict_table  # noqa: E402
from spiral_semantic_stages.neighbors import candidates_from_neighbors  # noqa: E402
from spiral_semantic_stages.pipeline import check_semantic_contradictions_stages  # noqa: E402
from spiral_semantic_stages.settings import SpiralSemanticSettings  # noqa: E402
import spiral_semantic_stages.pipeline as _pipeline_mod  # noqa: E402

_ORIGINAL_SPARSECL_AVAILABLE = _pipeline_mod.sparsecl_available

RDL = _BTC / "real-data-lab"
DEFAULT_SKF = RDL / "Project Core Platform.skf.json"
DEFAULT_BENIGN = RDL / "list_benign_semantic_focus.md"
DEFAULT_CONFLICT = RDL / "list_conflict_semantic_only.md"

# Default: include neighbors down to this cosine when building the candidate pool; pipeline applies cfg threshold.
DEFAULT_POOL_SIM_FLOOR = 0.32
POOL_LIMIT = 48


def _load_skf_facts(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    facts = data.get("facts") or []
    out: list[dict[str, Any]] = []
    for f in facts:
        k = (f.get("key") or "").strip()
        v = (f.get("value") or "").strip()
        if k and v:
            out.append({"key": k, "body": v})
    return out


def _embed_corpus_sentence_transformers(model_name: str, texts: list[str]) -> list[list[float]]:
    from sentence_transformers import SentenceTransformer

    m = SentenceTransformer(model_name)
    embs = m.encode(texts, convert_to_numpy=True, show_progress_bar=False)
    return [row.astype(float).tolist() for row in embs]


def _embed_corpus_openai(model: str, texts: list[str], api_key: str | None) -> list[list[float]]:
    key = (api_key or os.environ.get("OPENAI_API_KEY") or "").strip()
    if not key:
        raise SystemExit("OpenAI embeddings require OPENAI_API_KEY or --openai-api-key.")

    from openai import OpenAI

    client = OpenAI(api_key=key)
    return _embed_batches_openai_compatible(client, model, texts)


def _normalize_openrouter_base(url: str) -> str:
    """OpenRouter embeddings use .../api/v1/embeddings; strip /chat/completions if pasted from chat config."""
    u = (url or "").strip()
    if not u:
        return "https://openrouter.ai/api/v1"
    u = u.rstrip("/")
    for suffix in ("/chat/completions", "/completions"):
        if u.endswith(suffix):
            u = u[: -len(suffix)].rstrip("/")
            break
    if not u.endswith("/v1"):
        if "/api/v1" in u:
            idx = u.find("/api/v1")
            u = u[: idx + len("/api/v1")]
        elif u.endswith("/api"):
            u = u + "/v1"
        else:
            u = u.rstrip("/") + "/api/v1"
    return u


def _embed_corpus_openrouter(
    model: str,
    texts: list[str],
    *,
    api_key: str | None,
    base_url: str | None,
) -> list[list[float]]:
    key = (api_key or os.environ.get("OPENROUTER_API_KEY") or "").strip()
    if not key:
        raise SystemExit(
            "OpenRouter embeddings require OPENROUTER_API_KEY in spiral_semantic_stages/.env (or --openrouter-api-key).",
        )
    base = _normalize_openrouter_base((base_url or os.environ.get("OPENROUTER_BASE_URL") or "").strip())

    from openai import OpenAI

    client = OpenAI(api_key=key, base_url=base)
    return _embed_batches_openai_compatible(client, model, texts)


def _embed_batches_openai_compatible(client: Any, model: str, texts: list[str]) -> list[list[float]]:
    out: list[list[float] | None] = [None] * len(texts)
    batch_size = 100
    for start in range(0, len(texts), batch_size):
        batch = texts[start : start + batch_size]
        resp = client.embeddings.create(model=model, input=batch)
        for item in resp.data:
            out[start + item.index] = list(item.embedding)
    if any(v is None for v in out):
        raise RuntimeError("Embedding response missing indices")
    return [v for v in out if v is not None]


def _load_spiral_semantic_dotenv() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    p = _SOL / "spiral_semantic_stages" / ".env"
    if p.is_file():
        load_dotenv(p)


def _parse_float_list(s: str) -> list[float]:
    return [float(x.strip()) for x in s.split(",") if x.strip()]


def _parse_manual_cfg(params: str, sparsecl_model: str) -> SpiralSemanticSettings:
    parts = [p.strip() for p in params.split(",")]
    if len(parts) != 5:
        raise SystemExit("--per-row-params expects exactly 5 comma-separated fields: sim,nli,floor,high,ev")
    ev = parts[4].lower() in ("1", "true", "yes", "t")
    return SpiralSemanticSettings(
        conflict_embedding_similarity_threshold=float(parts[0]),
        nli_contradiction_confidence_threshold=float(parts[1]),
        sparsity_entailment_floor=float(parts[2]),
        contradiction_high_severity_similarity=float(parts[3]),
        sparsecl_everify_enabled=ev,
        sparsecl_model=sparsecl_model,
        sparsecl_alpha=1.0,
    )


@dataclass
class SweepResult:
    cfg: SpiralSemanticSettings
    benign_fp: int
    benign_total: int
    conflict_tp: int
    conflict_total: int
    stack: str = "as_config"

    # Binary detection: positive = semantic contradiction (should alert), negative = benign (should not).
    @property
    def tp(self) -> int:
        return self.conflict_tp

    @property
    def fn(self) -> int:
        return self.conflict_total - self.conflict_tp

    @property
    def fp(self) -> int:
        return self.benign_fp

    @property
    def tn(self) -> int:
        return self.benign_total - self.benign_fp

    @property
    def precision(self) -> float:
        d = self.tp + self.fp
        return self.tp / d if d else float("nan")

    @property
    def recall(self) -> float:
        d = self.tp + self.fn
        return self.tp / d if d else float("nan")

    @property
    def specificity(self) -> float:
        d = self.tn + self.fp
        return self.tn / d if d else float("nan")

    @property
    def npv(self) -> float:
        d = self.tn + self.fn
        return self.tn / d if d else float("nan")

    @property
    def accuracy(self) -> float:
        d = self.tp + self.tn + self.fp + self.fn
        return (self.tp + self.tn) / d if d else float("nan")

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        if math.isnan(p) or math.isnan(r) or p + r == 0:
            return float("nan")
        return 2 * p * r / (p + r)

    @property
    def fpr(self) -> float:
        """False positive rate on negatives (benign): FP / (FP + TN)."""
        d = self.fp + self.tn
        return self.fp / d if d else float("nan")

    @property
    def fnr(self) -> float:
        """Miss rate on positives: FN / (TP + FN)."""
        d = self.tp + self.fn
        return self.fn / d if d else float("nan")

    @property
    def benign_fn_rate(self) -> float:
        return self.benign_fp / self.benign_total if self.benign_total else 0.0

    @property
    def conflict_recall(self) -> float:
        return self.conflict_tp / self.conflict_total if self.conflict_total else 0.0


def _apply_cfg_overrides(
    cfg: SpiralSemanticSettings,
    overrides: dict[str, Any] | None,
) -> SpiralSemanticSettings:
    if not overrides:
        return cfg
    return cfg.model_copy(update=overrides)


def _eval_config(
    cfg: SpiralSemanticSettings,
    benign_rows: list[dict[str, Any]],
    conflict_rows: list[dict[str, Any]],
    neighbors_by_key: dict[str, ExistingFact],
    neighbor_list: list[ExistingFact],
    *,
    stack: str = "as_config",
    pool_sim_floor: float = DEFAULT_POOL_SIM_FLOOR,
    cfg_overrides: dict[str, Any] | None = None,
) -> SweepResult:
    cfg = _apply_cfg_overrides(cfg, cfg_overrides)
    b_fp = 0
    for row in benign_rows:
        key = row["proposed_key"]
        body = row["body"]
        prop = FactProposal(key=key, body=body, embedding=neighbors_by_key[key].embedding)
        cands = candidates_from_neighbors(
            prop,
            neighbor_list,
            similarity_threshold=pool_sim_floor,
            limit=POOL_LIMIT,
        )
        hits = check_semantic_contradictions_stages(
            key,
            body,
            cands,
            settings=cfg,
            limit=10,
            proposed_kind=row.get("proposed_kind"),
        )
        if hits:
            b_fp += 1

    c_tp = 0
    for row in conflict_rows:
        key = row["proposed_key"]
        body = row["body"]
        prop = FactProposal(key=key, body=body, embedding=neighbors_by_key[key].embedding)
        cands = candidates_from_neighbors(
            prop,
            neighbor_list,
            similarity_threshold=pool_sim_floor,
            limit=POOL_LIMIT,
        )
        hits = check_semantic_contradictions_stages(
            key,
            body,
            cands,
            settings=cfg,
            limit=10,
            proposed_kind=row.get("proposed_kind"),
        )
        if hits:
            c_tp += 1

    return SweepResult(
        cfg=cfg,
        benign_fp=b_fp,
        benign_total=len(benign_rows),
        conflict_tp=c_tp,
        conflict_total=len(conflict_rows),
        stack=stack,
    )


def _settings_grid(
    sims: list[float],
    nlis: list[float],
    floors: list[float],
    high_sims: list[float],
    alphas: list[float],
    everify: list[bool],
    sparsecl_model: str,
) -> Iterable[SpiralSemanticSettings]:
    for sim, nli, floor, high, alpha, ev in itertools.product(sims, nlis, floors, high_sims, alphas, everify):
        yield SpiralSemanticSettings(
            conflict_embedding_similarity_threshold=sim,
            nli_contradiction_confidence_threshold=nli,
            sparsity_entailment_floor=floor,
            contradiction_high_severity_similarity=high,
            sparsecl_alpha=alpha,
            sparsecl_everify_enabled=ev,
            sparsecl_model=sparsecl_model,
        )


def _pct(x: float, *, digits: int = 2) -> str:
    if isinstance(x, float) and math.isnan(x):
        return ""
    return f"{100.0 * float(x):.{digits}f}"


def _row_dict(r: SweepResult) -> dict[str, Any]:
    c = r.cfg
    return {
        "stack": r.stack,
        "embed_sim_threshold": c.conflict_embedding_similarity_threshold,
        "nli_contra_threshold": c.nli_contradiction_confidence_threshold,
        "sparsity_floor": c.sparsity_entailment_floor,
        "high_severity_sim": c.contradiction_high_severity_similarity,
        "sparsecl_alpha": c.sparsecl_alpha,
        "sparsecl_everify": c.sparsecl_everify_enabled,
        "nli_predicate_overlap_threshold": c.nli_predicate_overlap_threshold,
        "nli_bidirectional_enabled": c.nli_bidirectional_enabled,
        "nli_margin_threshold": c.nli_contradiction_margin_threshold,
        "TP": r.tp,
        "FN": r.fn,
        "FP": r.fp,
        "TN": r.tn,
        "precision_pct": _pct(r.precision),
        "recall_pct": _pct(r.recall),
        "specificity_pct": _pct(r.specificity),
        "npv_pct": _pct(r.npv),
        "accuracy_pct": _pct(r.accuracy),
        "f1_pct": _pct(r.f1),
        "fpr_pct": _pct(r.fpr),
        "fnr_pct": _pct(r.fnr),
    }


def _write_report_csv(path: Path, rows: list[SweepResult]) -> None:
    fieldnames = [
        "stack",
        "embed_sim_threshold",
        "nli_contra_threshold",
        "sparsity_floor",
        "high_severity_sim",
        "sparsecl_alpha",
        "sparsecl_everify",
        "nli_predicate_overlap_threshold",
        "nli_bidirectional_enabled",
        "nli_margin_threshold",
        "TP",
        "FN",
        "FP",
        "TN",
        "precision_pct",
        "recall_pct",
        "specificity_pct",
        "npv_pct",
        "accuracy_pct",
        "f1_pct",
        "fpr_pct",
        "fnr_pct",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(_row_dict(r))


def _write_report_md(
    path: Path,
    rows: list[SweepResult],
    *,
    embed_label: str,
    skf_path: Path,
    benign_path: Path,
    conflict_path: Path,
    benign_n: int,
    conflict_n: int,
    pool_floor: float,
    stacking_summary: str,
    gate_summary: str,
) -> None:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    by_f1 = sorted(
        rows,
        key=lambda r: (-(r.f1 if not math.isnan(r.f1) else -1), -r.precision if not math.isnan(r.precision) else -1),
    )
    top = by_f1[:15]
    multi_stack = len({r.stack for r in rows}) > 1
    total_n = benign_n + conflict_n

    lines: list[str] = [
        "# Semantic threshold mix report (precision, FP, and confusion matrix)",
        "",
        f"Generated (UTC): `{now}`",
        "",
        "## Setup",
        "",
        f"- **Stage-1 embeddings:** `{embed_label}`",
        f"- **SKF facts:** `{skf_path.as_posix()}`",
        f"- **Benign corpus:** `{benign_path.as_posix()}` ({benign_n} rows) — gold = no alert",
        f"- **Semantic-contradiction corpus:** `{conflict_path.as_posix()}` ({conflict_n} rows) — gold = alert",
        f"- **Candidate pool cosine floor:** `{pool_floor}` (pipeline threshold still applies per column)",
        f"- **Stacking:** {stacking_summary}",
        f"- **Gate overrides (research harness):** {gate_summary}",
        "",
        "## Replication limits",
        "",
        f"- **Labeled rows:** {total_n} total — adequate for coarse threshold search; small moves in F1/precision "
        "often do not replicate. Prefer a holdout slice of the markdown tables or a second corpus before locking prod.",
        "- **Embed space:** Cosine thresholds apply only in the same embedding model + normalization regime as "
        "production. Prefer `--embed-backend openrouter` (defaults when `OPENROUTER_API_KEY` is set) or "
        "`--embed-backend openai` to match Spirl before copying numeric gates into `.env`.",
        "- **Per-row forensics:** Use `--per-row-jsonl` with the same stack/embedder to get neighbor lists, "
        "SparseCL meta (recall guard, Hoyer), and NLI softmax triples per evaluated neighbor.",
        "",
        "## Definitions",
        "",
        "| Term | Meaning |",
        "|------|---------|",
        "| TP | Contradiction row: pipeline emitted ≥1 semantic hit |",
        "| FN | Contradiction row: no hit (missed) |",
        "| FP | Benign row: pipeline emitted ≥1 hit (false alert) |",
        "| TN | Benign row: no hit (correct silence) |",
        "| Precision | TP / (TP + FP) |",
        "| Recall | TP / (TP + FN) |",
        "| Specificity | TN / (TN + FP) |",
        "| NPV | TN / (TN + FN) |",
        "| FPR | FP / (FP + TN) — benign false-alarm rate |",
        "| FNR | FN / (TP + FN) — miss rate on contradictions |",
        "| Accuracy | (TP + TN) / total |",
        "",
        "_Percentages are 0–100. Empty cells = undefined (e.g. no positives in eval)._",
        "",
        "## Top configs by F1 (then precision)",
        "",
    ]
    top_hdr = (
        "| stack | embed_sim | nli | floor | high_sim | ev | TP | FN | FP | TN | Prec% | Rec% | Spec% | FPR% | FNR% | Acc% | F1% |"
        if multi_stack
        else "| embed_sim | nli | floor | high_sim | ev | TP | FN | FP | TN | Prec% | Rec% | Spec% | FPR% | FNR% | Acc% | F1% |"
    )
    top_sep = (
        "|-------|----------:|----:|------:|---------:|:--:|---:|---:|---:|---:|------:|-----:|------:|-----:|-----:|-----:|----:|"
        if multi_stack
        else "|----------:|----:|------:|---------:|:--:|---:|---:|---:|---:|------:|-----:|------:|-----:|-----:|-----:|----:|"
    )
    lines.extend([top_hdr, top_sep])
    for r in top:
        c = r.cfg
        base = (
            f"{c.conflict_embedding_similarity_threshold:.3f} | {c.nli_contradiction_confidence_threshold:.3f} | "
            f"{c.sparsity_entailment_floor:.3f} | {c.contradiction_high_severity_similarity:.3f} | "
            f"{'T' if c.sparsecl_everify_enabled else 'F'} | {r.tp} | {r.fn} | {r.fp} | {r.tn} | "
            f"{_pct(r.precision)} | {_pct(r.recall)} | {_pct(r.specificity)} | {_pct(r.fpr)} | {_pct(r.fnr)} | "
            f"{_pct(r.accuracy)} | {_pct(r.f1)} |"
        )
        lines.append(f"| `{r.stack}` | {base}" if multi_stack else f"| {base}")
    lines.extend(
        [
            "",
            f"## Full mix ({len(rows)} combinations)",
            "",
        ]
    )
    full_hdr = (
        "| stack | embed_sim | nli | floor | high_sim | α | ev | TP | FN | FP | TN | Prec% | Rec% | Spec% | FPR% | FNR% | Acc% | F1% |"
        if multi_stack
        else "| embed_sim | nli | floor | high_sim | α | ev | TP | FN | FP | TN | Prec% | Rec% | Spec% | FPR% | FNR% | Acc% | F1% |"
    )
    full_sep = (
        "|-------|----------:|----:|------:|---------:|--:|:--:|---:|---:|---:|---:|------:|-----:|------:|-----:|-----:|-----:|----:|"
        if multi_stack
        else "|----------:|----:|------:|---------:|--:|:--:|---:|---:|---:|---:|------:|-----:|------:|-----:|-----:|-----:|----:|"
    )
    lines.extend([full_hdr, full_sep])
    sort_full = sorted(
        rows,
        key=lambda r: (
            r.stack,
            r.cfg.conflict_embedding_similarity_threshold,
            r.cfg.nli_contradiction_confidence_threshold,
            r.cfg.sparsity_entailment_floor,
            r.cfg.contradiction_high_severity_similarity,
            r.cfg.sparsecl_alpha,
            r.cfg.sparsecl_everify_enabled,
        ),
    )
    for r in sort_full:
        c = r.cfg
        base = (
            f"{c.conflict_embedding_similarity_threshold:.3f} | {c.nli_contradiction_confidence_threshold:.3f} | "
            f"{c.sparsity_entailment_floor:.3f} | {c.contradiction_high_severity_similarity:.3f} | {c.sparsecl_alpha:.2f} | "
            f"{'T' if c.sparsecl_everify_enabled else 'F'} | {r.tp} | {r.fn} | {r.fp} | {r.tn} | "
            f"{_pct(r.precision)} | {_pct(r.recall)} | {_pct(r.specificity)} | {_pct(r.fpr)} | {_pct(r.fnr)} | "
            f"{_pct(r.accuracy)} | {_pct(r.f1)} |"
        )
        lines.append(f"| `{r.stack}` | {base}" if multi_stack else f"| {base}")
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def _format_env(cfg: SpiralSemanticSettings, *, sparsecl_model_for_env: str | None = None) -> str:
    sm = sparsecl_model_for_env if sparsecl_model_for_env else cfg.sparsecl_model
    lines = [
        "# Generated by semantic_benign_threshold_sweep.py - copy to Spirl backend if names match.",
        f"CONFLICT_EMBEDDING_SIMILARITY_THRESHOLD={cfg.conflict_embedding_similarity_threshold:.4f}".rstrip("0").rstrip("."),
        f"CONTRADICTION_HIGH_SEVERITY_SIMILARITY={cfg.contradiction_high_severity_similarity:.4f}".rstrip("0").rstrip("."),
        f"NLI_CONTRADICTION_CONFIDENCE_THRESHOLD={cfg.nli_contradiction_confidence_threshold:.4f}".rstrip("0").rstrip("."),
        f"SPARSECL_MODEL={sm}",
        f"SPARSECL_ALPHA={cfg.sparsecl_alpha:.4f}".rstrip("0").rstrip("."),
        f"SPARSITY_ENTAILMENT_FLOOR={cfg.sparsity_entailment_floor:.4f}".rstrip("0").rstrip("."),
        f"SPARSECL_EVERIFY_ENABLED={'true' if cfg.sparsecl_everify_enabled else 'false'}",
        "",
    ]
    return "\n".join(lines)


def _patch_sparsecl_off() -> None:
    """Stage 1.5 off: pipeline skips SparseCL (matches `sparsecl_available` false)."""

    def _no_sparsecl(_settings: Any = None) -> bool:
        return False

    _pipeline_mod.sparsecl_available = _no_sparsecl  # type: ignore[method-assign]


def _restore_sparsecl_pipeline() -> None:
    """Restore real SparseCL gating (reload Spiral-aligned Stage 1.5)."""

    _pipeline_mod.sparsecl_available = _ORIGINAL_SPARSECL_AVAILABLE  # type: ignore[method-assign]


def _cfg_for_stack(cfg: SpiralSemanticSettings, stack: str) -> SpiralSemanticSettings:
    if stack == "sparsecl_rerank_only":
        return cfg.model_copy(update={"sparsecl_everify_enabled": False})
    if stack == "sparsecl_everify_on":
        return cfg.model_copy(update={"sparsecl_everify_enabled": True})
    return cfg


def _apply_stack_mode(stack: str) -> None:
    if stack == "no_stage15":
        _patch_sparsecl_off()
    else:
        _restore_sparsecl_pipeline()


def _write_per_row_jsonl(
    path: Path,
    cfg: SpiralSemanticSettings,
    stack: str,
    benign_rows: list[dict[str, Any]],
    conflict_rows: list[dict[str, Any]],
    neighbors_by_key: dict[str, ExistingFact],
    neighbor_list: list[ExistingFact],
    *,
    pool_sim_floor: float = DEFAULT_POOL_SIM_FLOOR,
    cfg_overrides: dict[str, Any] | None = None,
) -> None:
    _apply_stack_mode(stack)
    cfg_use = _apply_cfg_overrides(_cfg_for_stack(cfg, stack), cfg_overrides)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in benign_rows:
            key = row["proposed_key"]
            body = row["body"]
            trace: dict[str, Any] = {}
            prop = FactProposal(key=key, body=body, embedding=neighbors_by_key[key].embedding)
            cands = candidates_from_neighbors(
                prop,
                neighbor_list,
                similarity_threshold=pool_sim_floor,
                limit=POOL_LIMIT,
            )
            hits = check_semantic_contradictions_stages(
                key,
                body,
                cands,
                settings=cfg_use,
                limit=10,
                proposed_kind=row.get("proposed_kind"),
                trace=trace,
            )
            rec = {
                "corpus_row_id": row.get("corpus_row_id"),
                "proposal_key": key,
                "gold_class": row.get("conflict_class"),
                "gold_should_alert": False,
                "predicted_alert": len(hits) > 0,
                "stack": stack,
                "pool_sim_floor": pool_sim_floor,
                "settings_snapshot": cfg_use.model_dump(),
                "hits": hits,
                "trace": trace,
            }
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        for row in conflict_rows:
            key = row["proposed_key"]
            body = row["body"]
            trace = {}
            prop = FactProposal(key=key, body=body, embedding=neighbors_by_key[key].embedding)
            cands = candidates_from_neighbors(
                prop,
                neighbor_list,
                similarity_threshold=pool_sim_floor,
                limit=POOL_LIMIT,
            )
            hits = check_semantic_contradictions_stages(
                key,
                body,
                cands,
                settings=cfg_use,
                limit=10,
                proposed_kind=row.get("proposed_kind"),
                trace=trace,
            )
            rec = {
                "corpus_row_id": row.get("corpus_row_id"),
                "proposal_key": key,
                "gold_class": row.get("conflict_class"),
                "gold_should_alert": True,
                "predicted_alert": len(hits) > 0,
                "stack": stack,
                "pool_sim_floor": pool_sim_floor,
                "settings_snapshot": cfg_use.model_dump(),
                "hits": hits,
                "trace": trace,
            }
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Grid-search semantic .env thresholds for benign FP vs semantic contradiction recall (local pipeline).",
    )
    ap.add_argument("--skf-json", type=Path, default=DEFAULT_SKF, help="SKF export with baseline facts")
    ap.add_argument("--benign-md", type=Path, default=DEFAULT_BENIGN, help="Benign markdown table")
    ap.add_argument("--conflict-md", type=Path, default=DEFAULT_CONFLICT, help="Semantic-contradiction markdown (for recall)")
    ap.add_argument("--no-conflict-eval", action="store_true", help="Only score benign FPs (skip conflict list)")
    ap.add_argument(
        "--embed-backend",
        choices=("sentence_transformers", "openai", "openrouter"),
        default=None,
        help="Stage-1 vectors: sentence_transformers | openai | openrouter (OpenAI-compatible). "
        "Default: openrouter if OPENROUTER_API_KEY is set after loading spiral_semantic_stages/.env, else sentence_transformers.",
    )
    ap.add_argument(
        "--embedding-model",
        default="all-mpnet-base-v2",
        metavar="NAME",
        help="When --embed-backend sentence_transformers: model id for cosine neighbors",
    )
    ap.add_argument(
        "--openai-embedding-model",
        default="text-embedding-3-small",
        metavar="NAME",
        help="When --embed-backend openai: embedding model id",
    )
    ap.add_argument(
        "--openai-api-key",
        default="",
        metavar="KEY",
        help="OpenAI API key (else env OPENAI_API_KEY)",
    )
    ap.add_argument(
        "--openrouter-api-key",
        default="",
        metavar="KEY",
        help="OpenRouter key (else env OPENROUTER_API_KEY after .env load)",
    )
    ap.add_argument(
        "--openrouter-base-url",
        default="",
        metavar="URL",
        help="OpenRouter OpenAI base, e.g. https://openrouter.ai/api/v1 (else OPENROUTER_BASE_URL; /chat/completions stripped)",
    )
    ap.add_argument(
        "--openrouter-embedding-model",
        default="",
        metavar="NAME",
        help="OpenRouter embedding model id (else OPENROUTER_EMBEDDING_MODEL, e.g. openai/text-embedding-3-small)",
    )
    ap.add_argument("--no-sparsecl", action="store_true", help="Force SparseCL off (faster; NLI + embedding gate only)")
    ap.add_argument(
        "--pool-sim-floor",
        type=float,
        default=DEFAULT_POOL_SIM_FLOOR,
        metavar="COS",
        help="Min cosine for Stage-1 candidate pool (before pipeline embed threshold); lower = more neighbors",
    )
    ap.add_argument(
        "--nli-predicate-overlap",
        type=float,
        default=None,
        metavar="J",
        help="Override Stage 1.75 Jaccard gate for all grid rows (0 disables predicate overlap gate)",
    )
    ap.add_argument(
        "--no-nli-bidirectional",
        action="store_true",
        help="Override: forward NLI only (disable bidirectional requirement) for all grid rows",
    )
    ap.add_argument(
        "--nli-margin-threshold",
        type=float,
        default=None,
        metavar="M",
        help="Override NLI margin gate for all grid rows (lower = easier to pass Stage 2)",
    )
    ap.add_argument(
        "--ablation-sparsecl",
        action="store_true",
        help="Run 3 stacks: no Stage 1.5, SparseCL rerank-only, SparseCL+E-Verify (same threshold grid each)",
    )
    ap.add_argument("--sparsecl-model", default="SparseCL/BGE-SparseCL-arguana", help="SparseCL checkpoint when enabled")
    ap.add_argument("--quick", action="store_true", help="Smaller default grids")
    ap.add_argument("--sim-grid", type=str, default="", help="Comma-separated CONFLICT_EMBEDDING_SIMILARITY_THRESHOLD values")
    ap.add_argument("--nli-grid", type=str, default="", help="Comma-separated NLI_CONTRADICTION_CONFIDENCE_THRESHOLD values")
    ap.add_argument("--floor-grid", type=str, default="", help="Comma-separated SPARSITY_ENTAILMENT_FLOOR values")
    ap.add_argument("--high-sim-grid", type=str, default="", help="Comma-separated CONTRADICTION_HIGH_SEVERITY_SIMILARITY")
    ap.add_argument("--alpha-grid", type=str, default="", help="Comma-separated SPARSECL_ALPHA values")
    ap.add_argument(
        "--everify-grid",
        type=str,
        default="",
        help="Comma-separated true/false for SPARSECL_EVERIFY_ENABLED (e.g. true,false)",
    )
    ap.add_argument("--write-env", type=Path, default=None, help="Write winning .env fragment to this path")
    ap.add_argument("--max-show", type=int, default=12, help="Print this many runner-up rows")
    ap.add_argument(
        "--staged-nli",
        action="store_true",
        help="Run multiple NLI threshold bands in order; stop when benign_fp==0 (saves time vs one huge grid)",
    )
    ap.add_argument(
        "--report-md",
        type=Path,
        default=None,
        metavar="PATH",
        help="Write markdown table: all threshold mixes with TP/FN/FP/TN, precision, FP rate (FPR), etc.",
    )
    ap.add_argument(
        "--report-csv",
        type=Path,
        default=None,
        metavar="PATH",
        help="Same data as CSV (percent columns are 0–100, not fractions).",
    )
    ap.add_argument(
        "--preset",
        choices=("default", "mix", "mix-wide"),
        default="default",
        help="mix / mix-wide: Cartesian grids for reports (default = use --quick or full grid)",
    )
    ap.add_argument(
        "--per-row-jsonl",
        type=Path,
        default=None,
        metavar="PATH",
        help="After sweep: write one JSON object per corpus row with trace (neighbors, SparseCL meta, NLI probs)",
    )
    ap.add_argument(
        "--per-row-stack",
        default="",
        metavar="ID",
        help="Stack for per-row trace: no_stage15 | sparsecl_rerank_only | sparsecl_everify_on | spiral_full "
        "(default: best row's stack from this run)",
    )
    ap.add_argument(
        "--per-row-params",
        default="",
        metavar="SIM,NLI,FLOOR,HIGH,EV",
        help="If set, override config for --per-row-jsonl only: e.g. 0.65,0.92,0.25,0.82,true",
    )
    args = ap.parse_args()

    _load_spiral_semantic_dotenv()

    if args.embed_backend is None:
        if os.environ.get("OPENROUTER_API_KEY", "").strip():
            args.embed_backend = "openrouter"
        else:
            args.embed_backend = "sentence_transformers"

    args.openrouter_embedding_model = (
        (args.openrouter_embedding_model or "").strip()
        or os.environ.get("OPENROUTER_EMBEDDING_MODEL", "").strip()
        or "openai/text-embedding-3-small"
    )

    if args.ablation_sparsecl and args.no_sparsecl:
        raise SystemExit("Use --ablation-sparsecl alone; it already includes a no-SparseCL pass.")

    cfg_overrides: dict[str, Any] = {}
    if args.nli_predicate_overlap is not None:
        cfg_overrides["nli_predicate_overlap_threshold"] = float(args.nli_predicate_overlap)
    if args.no_nli_bidirectional:
        cfg_overrides["nli_bidirectional_enabled"] = False
    if args.nli_margin_threshold is not None:
        cfg_overrides["nli_contradiction_margin_threshold"] = float(args.nli_margin_threshold)
    cfg_overrides_opt = cfg_overrides if cfg_overrides else None

    gate_summary_parts = [f"pool_sim_floor=`{args.pool_sim_floor}`"]
    if cfg_overrides:
        gate_summary_parts.append("overrides: " + ", ".join(f"{k}={v}" for k, v in cfg_overrides.items()))
    else:
        gate_summary_parts.append("no fixed overrides for predicate / bidirectional / margin (Spiral defaults on each row)")
    gate_summary = " ".join(gate_summary_parts)

    report_requested = bool(args.report_md or args.report_csv)

    if args.preset == "mix":
        sims = [0.50, 0.55, 0.60, 0.65, 0.70]
        nlis = [0.72, 0.76, 0.80, 0.84, 0.88, 0.92, 0.96]
        floors = [0.25, 0.35]
        high_sims = [0.82]
        alphas = [1.0]
        everify = [True]
    elif args.preset == "mix-wide":
        sims = [0.48, 0.54, 0.60, 0.66, 0.72, 0.78]
        nlis = [0.70, 0.75, 0.80, 0.85, 0.88, 0.90, 0.93, 0.96, 0.98]
        floors = [0.20, 0.35]
        high_sims = [0.78, 0.86]
        alphas = [1.0]
        everify = [True, False]
    elif args.quick:
        sims = [0.50, 0.58, 0.66, 0.74]
        nlis = [0.75, 0.82, 0.88, 0.94]
        floors = [0.20, 0.35]
        high_sims = [0.82]
        alphas = [1.0]
        everify = [True]
    else:
        sims = [0.48, 0.52, 0.56, 0.60, 0.64, 0.68, 0.72, 0.78]
        nlis = [0.70, 0.75, 0.80, 0.85, 0.88, 0.90, 0.93, 0.96]
        floors = [0.15, 0.25, 0.35, 0.45]
        high_sims = [0.78, 0.82, 0.86]
        alphas = [1.0]
        everify = [True, False]

    if args.sim_grid:
        sims = _parse_float_list(args.sim_grid)
    if args.nli_grid:
        nlis = _parse_float_list(args.nli_grid)
    if args.floor_grid:
        floors = _parse_float_list(args.floor_grid)
    if args.high_sim_grid:
        high_sims = _parse_float_list(args.high_sim_grid)
    if args.alpha_grid:
        alphas = _parse_float_list(args.alpha_grid)
    if args.everify_grid.strip():
        everify = [x.strip().lower() in ("1", "true", "yes") for x in args.everify_grid.split(",") if x.strip()]

    if not args.skf_json.is_file():
        raise SystemExit(f"Missing SKF: {args.skf_json}")
    if not args.benign_md.is_file():
        raise SystemExit(f"Missing benign list: {args.benign_md}")

    skf_facts = _load_skf_facts(args.skf_json)
    if not skf_facts:
        raise SystemExit("No facts in SKF JSON")

    benign_rows = parse_semantic_benign_table(args.benign_md)
    conflict_rows: list[dict[str, Any]] = []
    if not args.no_conflict_eval:
        if not args.conflict_md.is_file():
            raise SystemExit(f"Missing conflict list: {args.conflict_md}")
        conflict_rows = [r for r in parse_conflict_table(args.conflict_md) if r.get("conflict_class") == "semantic_contradiction"]

    keys_in_skf = {f["key"] for f in skf_facts}
    for row in benign_rows:
        for k in row["based_on_facts"]:
            if k not in keys_in_skf:
                print(f"warning: based_on fact {k!r} not in SKF (cosine neighbors may be off)", file=sys.stderr)

    texts: list[str] = []
    meta: list[tuple[str, str]] = []
    for f in skf_facts:
        texts.append(f["body"])
        meta.append(("fact", f["key"]))
    for row in benign_rows:
        texts.append(row["body"])
        meta.append(("benign", row["proposed_key"]))
    for row in conflict_rows:
        texts.append(row["body"])
        meta.append(("conflict", row["proposed_key"]))

    if args.embed_backend == "openai":
        embed_label = f"openai:{args.openai_embedding_model}"
    elif args.embed_backend == "openrouter":
        base_show = _normalize_openrouter_base(
            (args.openrouter_base_url or os.environ.get("OPENROUTER_BASE_URL") or "").strip(),
        )
        embed_label = f"openrouter:{args.openrouter_embedding_model} @ {base_show}"
    else:
        embed_label = f"sentence-transformers:{args.embedding_model}"
    print(f"Embedding {len(texts)} strings via {embed_label} ...", flush=True)
    if args.embed_backend == "openai":
        vectors = _embed_corpus_openai(
            args.openai_embedding_model,
            texts,
            (args.openai_api_key or "").strip() or None,
        )
    elif args.embed_backend == "openrouter":
        vectors = _embed_corpus_openrouter(
            args.openrouter_embedding_model,
            texts,
            api_key=(args.openrouter_api_key or "").strip() or None,
            base_url=(args.openrouter_base_url or "").strip() or None,
        )
    else:
        vectors = _embed_corpus_sentence_transformers(args.embedding_model, texts)

    neighbors_by_key: dict[str, ExistingFact] = {}
    neighbor_list: list[ExistingFact] = []
    for (kind, key), body, vec in zip(meta, texts, vectors, strict=True):
        ef = ExistingFact(key=key, body=body, embedding=vec, fact_id=key)
        if kind == "fact":
            neighbor_list.append(ef)
        neighbors_by_key[key] = ef

    nli_bands: list[list[float]]
    if args.staged_nli and not args.nli_grid:
        nli_bands = [
            [0.70, 0.75, 0.80, 0.85],
            [0.86, 0.88, 0.90, 0.92],
            [0.93, 0.94, 0.95, 0.96],
            [0.97, 0.98, 0.99, 0.995],
        ]
    else:
        nli_bands = [nlis]

    if args.ablation_sparsecl:
        stack_runs: list[tuple[str, bool]] = [
            ("no_stage15", True),
            ("sparsecl_rerank_only", False),
            ("sparsecl_everify_on", False),
        ]
        stacking_summary = (
            "Ablation: `no_stage15` (SparseCL bypassed), `sparsecl_rerank_only` (E-Verify forced off), "
            "`sparsecl_everify_on` (E-Verify forced on); same numeric grid each pass."
        )
    elif args.no_sparsecl:
        stack_runs = [("no_stage15", True)]
        stacking_summary = "SparseCL Stage 1.5 bypassed (--no-sparsecl)."
    else:
        stack_runs = [("spiral_full", False)]
        stacking_summary = (
            "Spiral-shaped path: SparseCL loads when available; `ev` column reflects grid "
            "(SPARSECL_EVERIFY_ENABLED)."
        )

    def sort_key(r: SweepResult) -> tuple[int, int, float, float, str]:
        return (
            r.benign_fp,
            -r.conflict_tp,
            -r.cfg.nli_contradiction_confidence_threshold,
            -r.cfg.conflict_embedding_similarity_threshold,
            r.stack,
        )

    results: list[SweepResult] = []
    global_i = 0
    for stack_label, patch_off in stack_runs:
        if patch_off:
            _patch_sparsecl_off()
        else:
            _restore_sparsecl_pipeline()
        print(
            f"=== Stack `{stack_label}` (sparsecl_available={'false' if patch_off else 'true'}) ===",
            flush=True,
        )

        for band_idx, band in enumerate(nli_bands):
            ncomb = len(sims) * len(band) * len(floors) * len(high_sims) * len(alphas) * len(everify)
            print(
                f"Stage {band_idx + 1}/{len(nli_bands)}: {len(band)} NLI x ... -> {ncomb} combos | "
                f"benign={len(benign_rows)} conflict={len(conflict_rows)} | pool_floor={args.pool_sim_floor}",
                flush=True,
            )
            for cfg0 in _settings_grid(sims, band, floors, high_sims, alphas, everify, args.sparsecl_model):
                cfg = _cfg_for_stack(cfg0, stack_label)
                global_i += 1
                if global_i == 1 or global_i % 20 == 0:
                    print(f"  ... eval #{global_i}", flush=True)
                results.append(
                    _eval_config(
                        cfg,
                        benign_rows,
                        conflict_rows,
                        neighbors_by_key,
                        neighbor_list,
                        stack=stack_label,
                        pool_sim_floor=args.pool_sim_floor,
                        cfg_overrides=cfg_overrides_opt,
                    )
                )

            if (
                args.staged_nli
                and not args.nli_grid
                and not report_requested
                and not args.ablation_sparsecl
            ):
                results.sort(key=sort_key)
                if results and results[0].benign_fp == 0:
                    print(f"Early stop: zero benign_fp after NLI band {band_idx + 1}", flush=True)
                    break

    results.sort(key=sort_key)
    best = results[0]

    _restore_sparsecl_pipeline()

    print()
    print("=== Best ===")
    print(
        f"stack={best.stack} | benign_fp={best.benign_fp}/{best.benign_total} "
        f"conflict_detected={best.conflict_tp}/{best.conflict_total}",
    )
    env_sparse = args.sparsecl_model if best.stack == "no_stage15" else None
    print(_format_env(best.cfg, sparsecl_model_for_env=env_sparse))

    if args.max_show > 0:
        print()
        print(f"=== Top {args.max_show} (sorted by benign_fp, then conflict recall) ===")
        for r in results[: args.max_show]:
            print(
                f"  fp={r.benign_fp} tp={r.conflict_tp}/{r.conflict_total} "
                f"sim={r.cfg.conflict_embedding_similarity_threshold:.3f} "
                f"nli={r.cfg.nli_contradiction_confidence_threshold:.3f} "
                f"floor={r.cfg.sparsity_entailment_floor:.3f} "
                f"high={r.cfg.contradiction_high_severity_similarity:.3f} "
                f"ev={r.cfg.sparsecl_everify_enabled} stack={r.stack}",
            )

    if args.write_env:
        args.write_env.parent.mkdir(parents=True, exist_ok=True)
        args.write_env.write_text(
            _format_env(best.cfg, sparsecl_model_for_env=env_sparse),
            encoding="utf-8",
        )
        print()
        print(f"Wrote {args.write_env}")

    conflict_display = args.conflict_md if not args.no_conflict_eval else Path("(conflict eval disabled)")

    if args.report_csv:
        _write_report_csv(args.report_csv, results)
        print(f"Wrote CSV report: {args.report_csv}", flush=True)
    if args.report_md:
        _write_report_md(
            args.report_md,
            results,
            embed_label=embed_label,
            skf_path=args.skf_json,
            benign_path=args.benign_md,
            conflict_path=conflict_display,
            benign_n=len(benign_rows),
            conflict_n=len(conflict_rows),
            pool_floor=args.pool_sim_floor,
            stacking_summary=stacking_summary,
            gate_summary=gate_summary,
        )
        print(f"Wrote markdown report: {args.report_md}", flush=True)

    if args.per_row_jsonl:
        pr_stack = (args.per_row_stack or "").strip() or best.stack
        allowed_stacks = frozenset(
            {"no_stage15", "sparsecl_rerank_only", "sparsecl_everify_on", "spiral_full"},
        )
        if pr_stack not in allowed_stacks:
            raise SystemExit(f"--per-row-stack must be one of: {', '.join(sorted(allowed_stacks))}")
        pr_cfg = _parse_manual_cfg(args.per_row_params, args.sparsecl_model) if args.per_row_params.strip() else best.cfg
        _write_per_row_jsonl(
            args.per_row_jsonl,
            pr_cfg,
            pr_stack,
            benign_rows,
            conflict_rows,
            neighbors_by_key,
            neighbor_list,
            pool_sim_floor=args.pool_sim_floor,
            cfg_overrides=cfg_overrides_opt,
        )
        print(f"Wrote per-row trace JSONL: {args.per_row_jsonl}", flush=True)

    if report_requested:
        return 0

    if best.benign_fp > 0:
        print()
        print(
            "No combination reached zero benign_fp. Try: higher --nli-grid, higher --sim-grid, "
            "--no-sparsecl, or a production-aligned --embedding-model.",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
