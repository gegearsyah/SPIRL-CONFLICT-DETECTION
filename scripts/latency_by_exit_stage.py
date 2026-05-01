#!/usr/bin/env python3
"""Latency-by-exit-stage aggregator for RDL snapshots.

Reads ``real-data-lab/research/real_data_lab_execution_log.jsonl`` (or an
archived snapshot), partitions rows by cascade exit stage, and emits a
markdown table of ``(exit_stage, n, median_ms, p95_ms)``.

Exit stage classification (in priority order):

1. ``deterministic_temporal``    -- temporal lane deterministically fired
2. ``structural_explicit``       -- structural/dependency/constraint
                                    lane returned ``detected``
3. ``semantic_fast_filter``      -- semantic lane exited before LLM
                                    (anchor veto, compatibility veto, etc.)
4. ``semantic_llm_judge``        -- LLM judge invoked
5. ``benign_all_clear``          -- all lanes cleared

Latency source: ``result.preflight_semantic.semantic_trace.total_latency_ms``
(the semantic-lane wall clock).  When ``total_cascade_latency_ms`` is
logged (post-runner-patch snapshots), that is preferred for the
``semantic_*`` buckets; otherwise we fall back to the semantic-trace
wall clock.  The deterministic / structural buckets rely on the patched
``preflight_latency_ms`` field when present.

Usage (from SPIRAL-RESEARCH root):

    python scripts/latency_by_exit_stage.py \\
        --log real-data-lab/research/real_data_lab_execution_log.jsonl \\
        --out real-data-lab/research/wave4_latency_by_exit_stage.md
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
from pathlib import Path
from typing import Any, Iterable


# Stop-reason -> exit stage mapping for the semantic plane.
# ``llm_judge_*`` and ``judge_budget_exhausted`` indicate the judge
# fired.  Everything else is a pre-LLM fast-filter exit.
_LLM_STOP_REASONS = {
    "llm_judge_contradiction",
    "llm_judge_consistent",
    "judge_budget_exhausted",
}


def classify_exit_stage(result: dict[str, Any]) -> str:
    """Return the exit stage bucket for a single RDL row result."""
    lane_verdicts = result.get("lane_verdicts") or {}
    det = (lane_verdicts.get("deterministic") or {}).get("verdict") or ""
    struct = (lane_verdicts.get("structural") or {}).get("verdict") or ""
    sem = (lane_verdicts.get("semantic") or {}).get("verdict") or ""

    # Stage 1 deterministic lane fires (temporal + explicit structural proofs).
    if det == "detected":
        detected_types = (lane_verdicts.get("deterministic") or {}).get(
            "detected_types", []
        )
        if any(t == "temporal_invalidation" for t in detected_types):
            return "deterministic_temporal"
        return "deterministic_other"

    # Stage 2/3 structural lane.
    if struct == "detected":
        return "structural_explicit"

    # Stage 4/5 semantic lane.
    if sem == "detected" or sem == "rejected" or sem == "clear":
        trace = (result.get("preflight_semantic") or {}).get("semantic_trace") or {}
        stop = str(trace.get("winning_stop_reason") or "").strip()
        if stop in _LLM_STOP_REASONS:
            return "semantic_llm_judge"
        if stop:
            return "semantic_fast_filter"
        if sem == "clear":
            return "benign_all_clear"
        return "semantic_unknown"

    return "benign_all_clear"


def extract_latency_ms(result: dict[str, Any]) -> float | None:
    """Best-available wall-clock latency for the row in milliseconds.

    Prefers ``total_cascade_latency_ms`` (post-patch).  Falls back to
    ``preflight_latency_ms`` (post-patch).  Finally uses the
    semantic-trace wall clock if no cascade-level latency exists.
    """
    for key in ("total_cascade_latency_ms", "preflight_latency_ms"):
        val = result.get(key)
        try:
            if val is not None and float(val) > 0:
                return float(val)
        except (TypeError, ValueError):
            continue

    trace = (result.get("preflight_semantic") or {}).get("semantic_trace") or {}
    val = trace.get("total_latency_ms")
    try:
        if val is not None and float(val) > 0:
            return float(val)
    except (TypeError, ValueError):
        pass
    return None


def percentile(values: list[float], p: float) -> float | None:
    """Return the ``p``th percentile (0-1) of ``values`` via nearest-rank."""
    if not values:
        return None
    s = sorted(values)
    k = min(len(s) - 1, max(0, int(math.ceil(p * len(s))) - 1))
    return s[k]


def iter_rows(path: Path) -> Iterable[dict[str, Any]]:
    """Yield every JSONL record whose ``result`` looks like an RDL row.

    Skips pure-polling records (``action == "notification_poll"``) and
    records without a ``result.lane_verdicts`` field.
    """
    with path.open("r", encoding="utf-8") as fh:
        for raw in fh:
            raw = raw.strip()
            if not raw:
                continue
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError:
                continue
            result = obj.get("result")
            if not isinstance(result, dict):
                continue
            if "lane_verdicts" not in result:
                # Only rows that went through the cascade carry
                # lane_verdicts.  Polling / acknowledgement records
                # lack this field.
                continue
            yield obj


def aggregate(rows: Iterable[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Group latency samples by exit stage."""
    buckets: dict[str, list[float]] = {}
    corpus_samples: list[float] = []
    for obj in rows:
        result = obj["result"]
        stage = classify_exit_stage(result)
        latency = extract_latency_ms(result)
        if latency is None:
            buckets.setdefault(stage, [])
            continue
        buckets.setdefault(stage, []).append(latency)
        corpus_samples.append(latency)

    out: dict[str, dict[str, Any]] = {}
    for stage, samples in sorted(buckets.items()):
        if not samples:
            out[stage] = {
                "n": 0,
                "median_ms": None,
                "p95_ms": None,
                "min_ms": None,
                "max_ms": None,
            }
            continue
        out[stage] = {
            "n": len(samples),
            "median_ms": statistics.median(samples),
            "p95_ms": percentile(samples, 0.95),
            "min_ms": min(samples),
            "max_ms": max(samples),
        }

    out["__corpus__"] = {
        "n": len(corpus_samples),
        "median_ms": statistics.median(corpus_samples) if corpus_samples else None,
        "p95_ms": percentile(corpus_samples, 0.95) if corpus_samples else None,
        "min_ms": min(corpus_samples) if corpus_samples else None,
        "max_ms": max(corpus_samples) if corpus_samples else None,
    }
    return out


def render_markdown(stats: dict[str, dict[str, Any]], source: Path) -> str:
    def fmt_ms(v: float | None) -> str:
        if v is None:
            return "--"
        if v >= 1000:
            return f"{v / 1000:.2f} s"
        return f"{v:.0f} ms"

    order = [
        "deterministic_temporal",
        "deterministic_other",
        "structural_explicit",
        "semantic_fast_filter",
        "semantic_llm_judge",
        "semantic_unknown",
        "benign_all_clear",
    ]
    seen = set(stats.keys())
    order = [s for s in order if s in seen and s != "__corpus__"] + [
        s for s in sorted(seen - set(order)) if s != "__corpus__"
    ]

    lines = [
        "# Latency by exit stage",
        "",
        f"Source: `{source.as_posix()}`",
        "",
        "| Exit stage | n | Median | p95 | Min | Max |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for stage in order:
        s = stats[stage]
        lines.append(
            f"| `{stage}` | {s['n']} | "
            f"{fmt_ms(s['median_ms'])} | {fmt_ms(s['p95_ms'])} | "
            f"{fmt_ms(s['min_ms'])} | {fmt_ms(s['max_ms'])} |"
        )
    if "__corpus__" in stats:
        c = stats["__corpus__"]
        lines.append(
            f"| **corpus** | **{c['n']}** | **{fmt_ms(c['median_ms'])}** | "
            f"**{fmt_ms(c['p95_ms'])}** | {fmt_ms(c['min_ms'])} | "
            f"{fmt_ms(c['max_ms'])} |"
        )
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- `deterministic_temporal` fires when the Stage 1 temporal lane "
            "(regression cues + anchor NLI) flags the row.  This bucket "
            "reads the patched `preflight_latency_ms` when present, otherwise "
            "falls back to the semantic-trace wall clock (overestimate).",
            "- `structural_explicit` fires when the Stage 2/3 structural "
            "proof lane returns `detected`.",
            "- `semantic_fast_filter` fires when the semantic lane exits "
            "via an anchor / compatibility / budget-exhaustion check "
            "before calling the LLM judge.",
            "- `semantic_llm_judge` fires when the LLM judge is invoked.  "
            "This is the expensive bucket and dominates the corpus p95.",
            "- The corpus row is the full-log aggregate; individual "
            "bucket counts sum to it.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--log",
        type=Path,
        default=Path("real-data-lab/research/real_data_lab_execution_log.jsonl"),
        help="Path to the RDL execution log (jsonl).",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("real-data-lab/research/wave4_latency_by_exit_stage.md"),
        help="Output markdown path.",
    )
    parser.add_argument(
        "--json",
        type=Path,
        default=None,
        help="Optional machine-readable JSON output path.",
    )
    args = parser.parse_args()

    if not args.log.exists():
        parser.error(f"execution log not found: {args.log}")

    rows = list(iter_rows(args.log))
    stats = aggregate(rows)
    md = render_markdown(stats, args.log)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(md, encoding="utf-8")
    print(f"wrote {args.out} ({len(rows)} rows, {len(stats) - 1} exit-stage buckets)")

    if args.json is not None:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(
            json.dumps(stats, indent=2, default=str),
            encoding="utf-8",
        )
        print(f"wrote {args.json}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
