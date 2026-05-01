# Realistic slice (`paper3_realistic_slice.jsonl`)

## What this is

Twenty-four rows sampled from `paper3_execution_log.experiment_C.jsonl` (six per conflict class, spread across the 50-per-class pool using indices 0, 9, 18, 27, 36, 45). Each row keeps the **original** `fact_keys`, `conflict_class` (gold), and `injection_number` from Experiment C so replay against the same Neo4j state remains valid.

This is **not** independent real-world data: it is a **curated subsample** of the same synthetic injection run, documented for transparency and for separate reporting (e.g. “slice replay”) without re-scoring all 200 rows.

## Relation to ADR / ConflictBank

- **ADR-style prose**: the underlying fact bodies live in `paper3_basis.skf.json` and were authored for Paper 3 corpora (data-pipeline / SaaS / API-service themes), not scraped from external ADR repositories.
- **ConflictBank**: this slice is **not** derived from the ConflictBank benchmark; taxonomy alignment remains via citation to Su et al. (ConflictBank) in the paper, not via dataset transfer.

## How to replay

From `Beyond Temporal Contradiction/state-orchestration-lab/`:

```text
python replay_governance_log.py --log-name paper3_realistic_slice.jsonl --all-profiles --nli-oracle --summary-json results/paper3_realistic_slice_ablation.json
```

Omit `--nli-oracle` and install `requirements-eval.txt` for cross-encoder NLI (recommended for semantic ablations).
