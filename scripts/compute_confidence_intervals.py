#!/usr/bin/env python3
"""Wilson 95% CIs + McNemar p-values for Table 2 / Table 3 headline numbers.

Reads RDL and / or TAL execution logs, extracts the per-row (expected,
predicted, binary-hit) tuple for every scored row, then:

- computes **Wilson 95 %** score intervals for every proportion metric
  reported in the paper's main result tables;
- computes **McNemar exact binomial** p-values for Wave 3 vs Wave 4
  ablation contrasts when both logs are provided and the rows are
  paired by ``corpus_row_id``;
- falls back to a **two-proportion z-test** p-value when only one log
  is available in full (e.g. the Wave 3 baseline log in
  ``archive/full_redo_from_import_2026-04-15_180344Z`` is truncated to
  6 rows and only aggregate per-type counts from the matching
  ``real_data_lab_confusion_matrix.md`` file are recoverable).

The paper's §5.1 corpus-scale defense (task R1b) cites this script's
output.  Each Wave 3 vs Wave 4 per-type recall delta is reported with
its p-value so the paper can state honestly which deltas are within
noise.

Usage::

    python scripts/compute_confidence_intervals.py \\
        --wave4-log real-data-lab/research/archive/wave4_target_2026-04-21_final/real_data_lab_execution_log.jsonl \\
        --wave3-counts real-data-lab/research/wave3_baseline_counts.json \\
        --tal-log trusted-adr-lab/research/trusted_adr_lab_execution_log.jsonl \\
        --out real-data-lab/research/wave4_confidence_intervals.md \\
        --json real-data-lab/research/wave4_confidence_intervals.json
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Iterable


_Z_95 = 1.959963984540054  # two-sided 95% normal quantile

_CORE4_TYPES = (
    "temporal_invalidation",
    "constraint_violation",
    "dependency_impact",
    "semantic_contradiction",
)


# ─── Proportion helpers ─────────────────────────────────────────────────

def wilson_ci(k: int, n: int, z: float = _Z_95) -> tuple[float, float, float]:
    """Return (p_hat, lo, hi) for the Wilson score interval.

    ``k`` = # successes, ``n`` = # trials.  When ``n == 0`` returns
    ``(float('nan'), float('nan'), float('nan'))``.
    """
    if n <= 0:
        return float("nan"), float("nan"), float("nan")
    p = k / n
    denom = 1.0 + z * z / n
    center = (p + z * z / (2.0 * n)) / denom
    half = (
        z
        * math.sqrt(p * (1.0 - p) / n + z * z / (4.0 * n * n))
        / denom
    )
    return p, max(0.0, center - half), min(1.0, center + half)


def two_proportion_z(k1: int, n1: int, k2: int, n2: int) -> float | None:
    """Two-proportion z-test two-sided p-value.

    Returns ``None`` when inputs are degenerate.  Used as the fallback
    when McNemar pairing is unavailable.
    """
    if n1 <= 0 or n2 <= 0:
        return None
    p1, p2 = k1 / n1, k2 / n2
    pooled = (k1 + k2) / (n1 + n2)
    if pooled <= 0 or pooled >= 1:
        return 1.0
    se = math.sqrt(pooled * (1 - pooled) * (1 / n1 + 1 / n2))
    if se <= 0:
        return 1.0
    z = (p1 - p2) / se
    # two-sided p: 2 * (1 - Phi(|z|)); use erf.
    return 2.0 * (1.0 - 0.5 * (1.0 + math.erf(abs(z) / math.sqrt(2.0))))


# ─── McNemar exact-binomial ─────────────────────────────────────────────

def _binomial_coeff(n: int, k: int) -> int:
    if k < 0 or k > n:
        return 0
    k = min(k, n - k)
    num = 1
    den = 1
    for i in range(k):
        num *= n - i
        den *= i + 1
    return num // den


def mcnemar_exact(b: int, c: int) -> float:
    """Two-sided McNemar exact binomial p-value.

    ``b`` = # rows where system A is right and B is wrong.
    ``c`` = # rows where A is wrong and B is right.  Returns 1.0 when
    b == c == 0.  For b + c >= 25, uses the continuity-corrected
    chi-square approximation.
    """
    n = b + c
    if n == 0:
        return 1.0
    if n < 25:
        tail = min(b, c)
        prob = 0.0
        for k in range(tail + 1):
            prob += _binomial_coeff(n, k) * (0.5 ** n)
        return min(1.0, 2.0 * prob)
    chi2 = (abs(b - c) - 1.0) ** 2 / n
    # 1 df chi-square survival via complementary error function.
    return math.erfc(math.sqrt(chi2 / 2.0))


def mcnemar_counts(
    rows: dict[str, tuple[int, int]],
) -> tuple[int, int]:
    """Compute (b, c) McNemar counts from paired row outcomes.

    ``rows`` maps row_id -> (hit_A, hit_B) where each hit is 0 or 1.
    ``b`` = sum of rows where A=1, B=0.  ``c`` = sum of rows where A=0, B=1.
    """
    b = c = 0
    for _, (a, d) in rows.items():
        if a and not d:
            b += 1
        elif d and not a:
            c += 1
    return b, c


# ─── Log parsing ────────────────────────────────────────────────────────

def iter_scored_rows(path: Path) -> Iterable[dict[str, Any]]:
    """Yield scored RDL / TAL rows from an execution log.

    Only keeps records whose ``action`` is ``conflict_injected`` (RDL) or
    one of the TAL injection markers, and whose ``result.outcome_class``
    is a terminal verdict.
    """
    keep_actions = {
        "conflict_injected",
        "benign_injected",
        "ambiguity_injected",
        "row_injected",
    }
    with path.open("r", encoding="utf-8") as fh:
        for raw in fh:
            raw = raw.strip()
            if not raw:
                continue
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if obj.get("action") not in keep_actions:
                continue
            result = obj.get("result")
            if not isinstance(result, dict):
                continue
            yield obj


def row_outcomes(obj: dict[str, Any]) -> dict[str, Any]:
    """Reduce a scored row to the fields we need for metrics.

    Note on governance recovery: when the dedicated
    ``result.governance_outcome`` field is absent (pre-patch logger
    gap), we reconstruct it from ``final_conflict_type`` and
    ``winning_detector_plane``.  The canonical Wave 4 snapshot stores
    governance-selector verdicts with ``final_conflict_type =
    "needs_review"`` and ``winning_detector_plane =
    "governance_selector"``; this reconstruction is lossless with
    respect to the abstention decision.
    """
    result = obj["result"]
    expected = (
        str(obj.get("conflict_class") or result.get("expected_conflict_type") or "").strip()
    )
    predicted = str(result.get("final_conflict_type") or "").strip()
    outcome = str(result.get("outcome_class") or "").strip()
    governance = str(result.get("governance_outcome") or "").strip()
    plane = str(result.get("winning_detector_plane") or "").strip()

    if not governance:
        if predicted == "needs_review" or plane == "governance_selector":
            governance = "needs_review"
        elif outcome == "detected" and predicted and predicted != "needs_review":
            governance = "typed_conflict"
        elif outcome in {"clear", "abstain", ""}:
            governance = "benign"

    return {
        "corpus_row_id": str(obj.get("corpus_row_id") or ""),
        "expected": expected,
        "predicted": predicted,
        "outcome_class": outcome,
        "governance_outcome": governance,
        "winning_detector_plane": plane,
    }


# ─── Metric definitions ─────────────────────────────────────────────────

def compute_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute count-based metrics from scored rows.

    Returns a dict where each metric is ``{"k": int, "n": int,
    "p_hat": float, "ci_lo": float, "ci_hi": float}``.
    """
    out: dict[str, Any] = {}

    # Binary classification counts.  We report TWO views:
    #
    #   strict    -- anything that fires (outcome_class == "detected")
    #                is a positive prediction, even when governance
    #                routed it to ``needs_review``.  This matches the
    #                paper's Table 2 definition.
    #
    #   abstain_aware -- rows routed to ``needs_review`` are withheld
    #                from the binary tally and reported as abstentions.
    #                This matches AbstentionBench (arXiv:2506.09038) and
    #                El-Yaniv & Wiener (2010).  The numbers diverge from
    #                ``strict`` when governance is active — which is the
    #                whole point.
    #
    # ``ambiguous_case`` rows are excluded from the binary tally in
    # both views (they live under governance metrics).
    tp_s = fp_s = tn_s = fn_s = 0
    tp_a = fp_a = tn_a = fn_a = 0
    abstain_on_conflict = abstain_on_benign = 0
    for r in rows:
        expected = r["expected"]
        if expected == "ambiguous_case":
            continue
        expected_is_conflict = expected not in {"", "benign"}
        is_abstain = (
            r["governance_outcome"] == "needs_review"
            or r["predicted"] == "needs_review"
        )
        fired_strict = r["outcome_class"] == "detected"
        fired_abstain_aware = fired_strict and not is_abstain

        # strict
        if expected_is_conflict and fired_strict:
            tp_s += 1
        elif expected_is_conflict and not fired_strict:
            fn_s += 1
        elif (not expected_is_conflict) and fired_strict:
            fp_s += 1
        else:
            tn_s += 1

        # abstain-aware
        if is_abstain:
            if expected_is_conflict:
                abstain_on_conflict += 1
            else:
                abstain_on_benign += 1
            continue
        if expected_is_conflict and fired_abstain_aware:
            tp_a += 1
        elif expected_is_conflict and not fired_abstain_aware:
            fn_a += 1
        elif (not expected_is_conflict) and fired_abstain_aware:
            fp_a += 1
        else:
            tn_a += 1

    # Primary (paper-equivalent) binary metrics from strict scoring.
    tp, fp, tn, fn = tp_s, fp_s, tn_s, fn_s

    prec_k, prec_n = tp, tp + fp
    rec_k, rec_n = tp, tp + fn
    out["binary_precision"] = _ci_entry(prec_k, prec_n)
    out["binary_recall"] = _ci_entry(rec_k, rec_n)
    # Binary F1 is derived; its CI is approximated via the Wilson CI on
    # the micro-averaged denominator (2*TP / (2*TP + FP + FN)).  We
    # report it alongside the component CIs rather than claiming a tight
    # analytical CI on F1 itself.
    f1_k, f1_n = 2 * tp, 2 * tp + fp + fn
    out["binary_f1_mass"] = _ci_entry(f1_k, f1_n)

    # Specificity / benign FP rate.
    out["benign_specificity"] = _ci_entry(tn, tn + fp)
    out["benign_fp_rate"] = _ci_entry(fp, tn + fp)

    # Abstention summary (excluded from binary).
    out["abstain_on_conflict"] = _ci_entry(abstain_on_conflict, len(rows))
    out["abstain_on_benign"] = _ci_entry(abstain_on_benign, len(rows))

    # Secondary abstention-aware binary metrics (for the Limitations
    # discussion and to document that the paper's strict scoring is
    # conservative w.r.t. governance abstentions).
    out["binary_precision_abstain_aware"] = _ci_entry(tp_a, tp_a + fp_a)
    out["binary_recall_abstain_aware"] = _ci_entry(tp_a, tp_a + fn_a)
    out["binary_f1_mass_abstain_aware"] = _ci_entry(
        2 * tp_a, 2 * tp_a + fp_a + fn_a
    )
    out["benign_fp_rate_abstain_aware"] = _ci_entry(fp_a, tn_a + fp_a)

    # Per-type exact-type recall (core-4 + ambiguous special handling).
    per_type_counts: dict[str, tuple[int, int]] = {}
    for ct in _CORE4_TYPES + ("ambiguous_case",):
        k = 0
        n = 0
        for r in rows:
            if r["expected"] != ct:
                continue
            n += 1
            if ct == "ambiguous_case":
                if r["governance_outcome"] == "needs_review":
                    k += 1
            else:
                if r["predicted"] == ct:
                    k += 1
        if n:
            per_type_counts[ct] = (k, n)
            out[f"exact_recall_{ct}"] = _ci_entry(k, n)

    core4_k = sum(v[0] for t, v in per_type_counts.items() if t in _CORE4_TYPES)
    core4_n = sum(v[1] for t, v in per_type_counts.items() if t in _CORE4_TYPES)
    if core4_n:
        out["exact_recall_core4"] = _ci_entry(core4_k, core4_n)
    # TAL: core-3 (no dependency_impact substrate).
    core3_k = sum(
        v[0]
        for t, v in per_type_counts.items()
        if t in {"temporal_invalidation", "constraint_violation", "semantic_contradiction"}
    )
    core3_n = sum(
        v[1]
        for t, v in per_type_counts.items()
        if t in {"temporal_invalidation", "constraint_violation", "semantic_contradiction"}
    )
    if core3_n:
        out["exact_recall_core3"] = _ci_entry(core3_k, core3_n)

    # Governance: unsafe forced-type on ambiguous rows, needs_review
    # precision/recall.
    ambig_rows = [r for r in rows if r["expected"] == "ambiguous_case"]
    if ambig_rows:
        forced = sum(
            1
            for r in ambig_rows
            if r["governance_outcome"] == "typed_conflict"
            and r["predicted"] in _CORE4_TYPES
        )
        out["unsafe_forced_type_ambig"] = _ci_entry(forced, len(ambig_rows))

        tp_rev = sum(1 for r in ambig_rows if r["governance_outcome"] == "needs_review")
        out["needs_review_recall_ambig"] = _ci_entry(tp_rev, len(ambig_rows))

    # needs_review precision (computed over all rows).
    all_rev = [r for r in rows if r["governance_outcome"] == "needs_review"]
    if all_rev:
        correct_rev = sum(1 for r in all_rev if r["expected"] == "ambiguous_case")
        out["needs_review_precision"] = _ci_entry(correct_rev, len(all_rev))

    return out


def _ci_entry(k: int, n: int) -> dict[str, Any]:
    p, lo, hi = wilson_ci(k, n)
    return {"k": k, "n": n, "p_hat": p, "ci_lo": lo, "ci_hi": hi}


# ─── Paired McNemar across two logs ─────────────────────────────────────

def paired_mcnemar_per_type(
    wave3_rows: list[dict[str, Any]],
    wave4_rows: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Compute McNemar per expected type for two paired row sets.

    Rows are matched on ``corpus_row_id``.  When a row is missing from
    one side the pair is silently dropped and counted in ``n_missing``.
    """
    w3_by_id = {r["corpus_row_id"]: r for r in wave3_rows if r["corpus_row_id"]}
    w4_by_id = {r["corpus_row_id"]: r for r in wave4_rows if r["corpus_row_id"]}

    ids = sorted(set(w3_by_id) & set(w4_by_id))
    missing = (
        len(wave3_rows) - len(ids),
        len(wave4_rows) - len(ids),
    )

    out: dict[str, dict[str, Any]] = {}
    for ct in _CORE4_TYPES:
        paired: dict[str, tuple[int, int]] = {}
        for rid in ids:
            r3, r4 = w3_by_id[rid], w4_by_id[rid]
            if r3["expected"] != ct:
                continue
            paired[rid] = (
                1 if r3["predicted"] == ct else 0,
                1 if r4["predicted"] == ct else 0,
            )
        if not paired:
            continue
        b, c = mcnemar_counts(paired)
        out[ct] = {
            "n_paired": len(paired),
            "wave3_correct": sum(x for x, _ in paired.values()),
            "wave4_correct": sum(y for _, y in paired.values()),
            "discordant_w3_only": b,
            "discordant_w4_only": c,
            "p_value": mcnemar_exact(b, c),
        }
    return {"per_type": out, "ids_matched": len(ids), "missing": missing}


# ─── Rendering ──────────────────────────────────────────────────────────

def fmt_pct(val: float | None) -> str:
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return "--"
    return f"{val:.4f}"


def fmt_ci(entry: dict[str, Any]) -> str:
    if entry["n"] == 0:
        return "-- (n=0)"
    return (
        f"{fmt_pct(entry['p_hat'])} "
        f"[{fmt_pct(entry['ci_lo'])}, {fmt_pct(entry['ci_hi'])}] "
        f"(n={entry['n']})"
    )


def render_table(
    title: str,
    metrics: dict[str, Any],
    label: str,
) -> list[str]:
    lines = [f"## {title} ({label})", ""]
    lines.append("| Metric | k / n | p̂ | 95% Wilson CI |")
    lines.append("| --- | ---: | ---: | ---: |")
    order = [
        "binary_precision",
        "binary_recall",
        "binary_f1_mass",
        "benign_specificity",
        "benign_fp_rate",
        "exact_recall_core4",
        "exact_recall_core3",
        "exact_recall_temporal_invalidation",
        "exact_recall_constraint_violation",
        "exact_recall_dependency_impact",
        "exact_recall_semantic_contradiction",
        "exact_recall_ambiguous_case",
        "unsafe_forced_type_ambig",
        "needs_review_recall_ambig",
        "needs_review_precision",
    ]
    order = [m for m in order if m in metrics] + [
        m for m in sorted(metrics) if m not in order
    ]
    for m in order:
        e = metrics[m]
        lines.append(
            f"| `{m}` | {e['k']} / {e['n']} | "
            f"{fmt_pct(e['p_hat'])} | "
            f"[{fmt_pct(e['ci_lo'])}, {fmt_pct(e['ci_hi'])}] |"
        )
    lines.append("")
    return lines


def render_mcnemar_section(
    mc: dict[str, Any],
    w3_metrics: dict[str, Any] | None,
    w4_metrics: dict[str, Any],
) -> list[str]:
    lines = ["## Wave 3 vs Wave 4 McNemar (RDL)", ""]
    if not mc or not mc.get("per_type"):
        lines.append(
            "_Paired McNemar unavailable: Wave 3 execution log is "
            "truncated.  Falling back to two-proportion z-test on "
            "aggregate counts where Wave 3 counts are recoverable._"
        )
        lines.append("")
        return lines

    lines.append(
        f"Paired rows matched on `corpus_row_id`: **{mc['ids_matched']}**.  "
        f"Unmatched rows (Wave 3 / Wave 4): **{mc['missing']}**."
    )
    lines.append("")
    lines.append(
        "| Type | n_paired | W3 correct | W4 correct | "
        "b (W3 only) | c (W4 only) | Exact McNemar p |"
    )
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: |")
    for ct, row in mc["per_type"].items():
        lines.append(
            f"| `{ct}` | {row['n_paired']} | "
            f"{row['wave3_correct']} | {row['wave4_correct']} | "
            f"{row['discordant_w3_only']} | {row['discordant_w4_only']} | "
            f"{row['p_value']:.4f} |"
        )
    lines.append("")
    lines.append(
        "_Exact McNemar p-value via two-sided binomial tail at "
        "n_discordant < 25; continuity-corrected chi-square "
        "approximation otherwise.  p >= 0.05 indicates the Wave 3 vs "
        "Wave 4 difference on this type is within chance at this sample "
        "size — state this honestly in the paper rather than hiding "
        "behind \"trend improvement\" language (plan R1b)._"
    )
    lines.append("")
    return lines


def render_fallback_section(
    w3_counts: dict[str, tuple[int, int]] | None,
    w4_metrics: dict[str, Any],
) -> list[str]:
    """When paired logs are unavailable, emit two-proportion z-test rows."""
    if not w3_counts:
        return []
    lines = ["## Wave 3 vs Wave 4 two-proportion z-test (unpaired fallback)", ""]
    lines.append(
        "_Wave 3 paired execution log is truncated; we fall back to a "
        "two-proportion z-test on the aggregate confusion-matrix counts "
        "recoverable from the archive.  This test has strictly less "
        "statistical power than McNemar on paired data.  When the R4 "
        "replay produces a full Wave 3 paired log, rerun this script to "
        "replace this table with the exact-binomial McNemar numbers._"
    )
    lines.append("")
    lines.append(
        "| Metric | W3 k/n | W4 k/n | W3 p̂ | W4 p̂ | Δ | two-prop p |"
    )
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: |")
    key_map = {
        "exact_recall_temporal_invalidation": "temporal_invalidation",
        "exact_recall_constraint_violation": "constraint_violation",
        "exact_recall_dependency_impact": "dependency_impact",
        "exact_recall_semantic_contradiction": "semantic_contradiction",
    }
    for metric, lookup in key_map.items():
        w3_kn = w3_counts.get(lookup)
        w4 = w4_metrics.get(metric)
        if not w3_kn or not w4:
            continue
        w3k, w3n = w3_kn
        w4k, w4n = w4["k"], w4["n"]
        p_value = two_proportion_z(w3k, w3n, w4k, w4n)
        w3_phat = w3k / w3n if w3n else float("nan")
        delta = (w4k / w4n if w4n else 0) - w3_phat
        lines.append(
            f"| `{metric}` | {w3k}/{w3n} | {w4k}/{w4n} | "
            f"{w3_phat:.4f} | {w4['p_hat']:.4f} | "
            f"{delta:+.4f} | "
            f"{(p_value if p_value is not None else float('nan')):.4f} |"
        )
    lines.append("")
    return lines


# ─── Main ───────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wave4-log", type=Path, required=True)
    parser.add_argument("--wave3-log", type=Path, default=None)
    parser.add_argument(
        "--wave3-counts",
        type=Path,
        default=None,
        help="JSON file with {type: [k, n]} aggregate counts for Wave 3 "
        "when the paired log is unavailable.",
    )
    parser.add_argument("--tal-log", type=Path, default=None)
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("real-data-lab/research/wave4_confidence_intervals.md"),
    )
    parser.add_argument("--json", type=Path, default=None)
    args = parser.parse_args()

    # Wave 4 RDL.
    w4_rows = [row_outcomes(o) for o in iter_scored_rows(args.wave4_log)]
    w4_metrics = compute_metrics(w4_rows)

    # Wave 3 RDL (paired if possible).
    mc_section: dict[str, Any] = {}
    w3_metrics: dict[str, Any] | None = None
    if args.wave3_log is not None and args.wave3_log.exists():
        w3_rows = [row_outcomes(o) for o in iter_scored_rows(args.wave3_log)]
        if len(w3_rows) >= 150:
            w3_metrics = compute_metrics(w3_rows)
            mc_section = paired_mcnemar_per_type(w3_rows, w4_rows)
        else:
            print(
                f"[warn] Wave 3 log has only {len(w3_rows)} scored rows; "
                "falling back to two-proportion z-test if --wave3-counts "
                "is provided."
            )

    # Wave 3 aggregate counts fallback.
    w3_counts: dict[str, tuple[int, int]] | None = None
    if args.wave3_counts is not None and args.wave3_counts.exists():
        raw = json.loads(args.wave3_counts.read_text(encoding="utf-8"))
        w3_counts = {
            k: (int(v[0]), int(v[1]))
            for k, v in raw.items()
            if not k.startswith("_") and isinstance(v, list) and len(v) == 2
        }

    # TAL.
    tal_metrics: dict[str, Any] | None = None
    if args.tal_log is not None and args.tal_log.exists():
        tal_rows = [row_outcomes(o) for o in iter_scored_rows(args.tal_log)]
        tal_metrics = compute_metrics(tal_rows)

    # Emit markdown.
    body: list[str] = [
        "# Wilson 95% CIs + McNemar / two-proportion z-test",
        "",
        "Script: `scripts/compute_confidence_intervals.py`",
        f"Wave 4 RDL log: `{args.wave4_log.as_posix()}`",
    ]
    if args.wave3_log:
        body.append(f"Wave 3 RDL log: `{args.wave3_log.as_posix()}`")
    if args.wave3_counts:
        body.append(f"Wave 3 aggregate counts: `{args.wave3_counts.as_posix()}`")
    if args.tal_log:
        body.append(f"TAL log: `{args.tal_log.as_posix()}`")
    body.append("")
    body.extend(
        [
            "## Binary scoring conventions",
            "",
            "We report two binary views:",
            "",
            "- **Strict** (`binary_precision`, `binary_recall`, `binary_f1_mass`, "
            "`benign_fp_rate`): any row whose `outcome_class == \"detected\"` is "
            "a positive prediction, even when governance routed it to "
            "`needs_review`.  This is the conservative scoring an adversarial "
            "reviewer would apply — the `needs_review` channel is \"the system "
            "raised an alarm\" regardless of whether it committed to a typed label.",
            "",
            "- **Abstention-aware** (`*_abstain_aware`, `abstain_on_*`): follows "
            "AbstentionBench (arXiv:2506.09038) and El-Yaniv & Wiener (2010).  "
            "Rows routed to `needs_review` are withheld from the binary tally "
            "and counted separately under `abstain_on_conflict` / "
            "`abstain_on_benign`.  The paper's Table 2 point estimates align "
            "with the abstention-aware view; the strict view is included so "
            "reviewers can audit the cost of treating every governance abstention "
            "as a typed fire.",
            "",
            "Both views are honest; they answer different questions.",
            "",
        ]
    )
    body.extend(render_table("RDL", w4_metrics, "Wave 4"))
    if w3_metrics:
        body.extend(render_table("RDL", w3_metrics, "Wave 3"))
    if tal_metrics:
        body.extend(render_table("TAL", tal_metrics, "Wave 4"))
    body.extend(render_mcnemar_section(mc_section, w3_metrics, w4_metrics))
    body.extend(render_fallback_section(w3_counts, w4_metrics))

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(body) + "\n", encoding="utf-8")
    print(f"wrote {args.out}")

    if args.json is not None:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(
            json.dumps(
                {
                    "wave4_rdl": w4_metrics,
                    "wave3_rdl": w3_metrics,
                    "tal_wave4": tal_metrics,
                    "mcnemar": mc_section,
                    "wave3_counts_fallback": w3_counts,
                },
                indent=2,
                default=str,
            ),
            encoding="utf-8",
        )
        print(f"wrote {args.json}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
