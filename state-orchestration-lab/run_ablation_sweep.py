#!/usr/bin/env python3
"""
Ablation sweep CLI entry point.

Each config runs the **hybrid cascade lab** (`kg_orchestrator/cascade_lab.py`): Stages 1--5
in cost order, temporal-only prune_set, plane arbitration, then post-arbitration binary scoring.

Run from state-orchestration-lab/:
  python run_ablation_sweep.py                        # run all configs
  python run_ablation_sweep.py --config A_base_unidirectional B_base_bidirectional
  python run_ablation_sweep.py --dry-run              # parse corpus, print counts
  python run_ablation_sweep.py --limit 5              # first 5 proposals only
  python run_ablation_sweep.py --skip-embedding       # reuse cached embeddings
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Ensure state-orchestration-lab is on the path
_LAB_DIR = Path(__file__).resolve().parent
if str(_LAB_DIR) not in sys.path:
    sys.path.insert(0, str(_LAB_DIR))

from dotenv import load_dotenv
load_dotenv(_LAB_DIR / ".env", override=False)
load_dotenv(_LAB_DIR / "spiral_semantic_stages" / ".env", override=False)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Run ablation sweep across pipeline configurations for mixed-workload evaluation"
    )
    ap.add_argument(
        "--config",
        nargs="+",
        default=None,
        help="Run specific configs by name (e.g. A_base_unidirectional). Default: all.",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse corpus only, print counts, do not run pipeline.",
    )
    ap.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Max proposals per config (0 = all).",
    )
    ap.add_argument(
        "--skip-embedding",
        action="store_true",
        help="Reuse cached embeddings (skip recomputation).",
    )
    ap.add_argument(
        "--top-k",
        type=int,
        default=10,
        help="Number of neighbors to retrieve per proposal (default: 10).",
    )
    ap.add_argument(
        "--threshold",
        type=float,
        default=0.35,
        help="Embedding similarity threshold for retrieval (default: 0.35).",
    )
    ap.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable debug logging.",
    )
    args = ap.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(name)-30s %(levelname)-5s %(message)s",
        datefmt="%H:%M:%S",
    )

    # ── Dry run ──────────────────────────────────────────────────────────────
    if args.dry_run:
        from corpus_loader import print_corpus_summary
        print_corpus_summary()
        return 0

    # ── Load configs ─────────────────────────────────────────────────────────
    from ablation_configs import get_configs
    try:
        configs = get_configs(args.config)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(f"\nAblation sweep: {len(configs)} config(s)")
    for c in configs:
        print(f"  {c.name}: {c.description}")
    print()

    # ── Run sweep ────────────────────────────────────────────────────────────
    from ablation_runner import run_sweep
    results = run_sweep(
        configs,
        limit=args.limit,
        skip_embedding=args.skip_embedding,
        retrieval_top_k=args.top_k,
        retrieval_threshold=args.threshold,
    )

    # ── Generate reports ─────────────────────────────────────────────────────
    from report_generator import generate_all
    paths = generate_all(results)

    print("\n" + "=" * 60)
    print("ABLATION SWEEP RESULTS")
    print("=" * 60)

    # Print summary table
    header = f"{'Config':<25} {'TP':>3} {'FP':>3} {'FN':>3} {'TN':>3}  {'Prec':>6} {'Rec':>6} {'F1':>6}  {'ms':>6}"
    print(header)
    print("-" * len(header))

    for r in results:
        s = r.to_summary_dict()
        print(
            f"{s['config']:<25} {s['TP']:>3} {s['FP']:>3} {s['FN']:>3} {s['TN']:>3}  "
            f"{s['precision']:>6.3f} {s['recall']:>6.3f} {s['f1']:>6.3f}  "
            f"{s['mean_latency_ms']:>6.0f}"
        )

    print()
    print("Reports written:")
    for key, path in paths.items():
        print(f"  {key}: {path}")
    print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
