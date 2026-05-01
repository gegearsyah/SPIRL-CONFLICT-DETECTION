# Phase 2 Report — Real Data Lab (Conflict injection)

Generated: 2026-04-10T19:29:40Z

## Corpus

- Source: `real-data-lab/list_conflict.md` (resolved: `C:\Users\GEYE ARDIANSYAH\Downloads\Innovation Hub\SPIRAL-RESEARCH\Beyond Temporal Contradiction\real-data-lab\list_conflict.md`)
- Mode: table-driven
- Project: `32f75297-7059-400e-9ec5-2439a87a866e`
- Rows attempted: **110**
- Injection limit applied: **False**

## Detection metrics (conflict corpus, `c-*` only)

Project: `32f75297-7059-400e-9ec5-2439a87a866e` · Source: `real-data-lab/list_conflict.md`

Scoring matches the mixed workload harness: semantic rows use `semantic_verdict` / trace; structural rows use preflight classes and async/notification fallbacks per `conflict_injected` log `result`.

| Metric | Value |
|--------|------:|
| Conflict rows scored (`conflict_injected`, c-*) | 110 |
| Binary detected (any alert) | 102 |
| Binary recall | 0.9273 |
| Exact-type matches | 75 |
| Exact-type recall | 0.6818 |
| Cross-type alerts | 21 |
| Abstained (no alert) | 8 |

## Per-class detection (conflict slice)

| conflict_class | injected | binary detected | binary recall | exact match | exact recall | cross-type | abstained |
|----------------|---------:|----------------:|--------------:|------------:|-------------:|-----------:|----------:|
| `semantic_contradiction` | 40 | 39 | 0.9750 | 38 | 0.9500 | 1 | 1 |
| `dependency_impact` | 20 | 19 | 0.9500 | 12 | 0.6000 | 7 | 1 |
| `constraint_violation` | 20 | 18 | 0.9000 | 11 | 0.5500 | 7 | 2 |
| `temporal_invalidation` | 20 | 20 | 1.0000 | 14 | 0.7000 | 6 | 0 |
| `ambiguous_case` | 10 | 6 | 0.6000 | 0 | 0.0000 | 0 | 4 |

## Exact-type confusion matrix (rows = gold `expected_conflict_type`, cols = derived prediction)

| Expected | semantic | dependency | constraint | temporal | none |
|----------|---------:|-----------:|-----------:|---------:|-----:|
| `semantic_contradiction` | 38 | 0 | 0 | 1 | 1 |
| `dependency_impact` | 3 | 12 | 2 | 2 | 1 |
| `constraint_violation` | 6 | 0 | 11 | 0 | 2 |
| `temporal_invalidation` | 4 | 2 | 0 | 14 | 0 |
| `ambiguous_case` | 5 | 0 | 1 | 0 | 4 |

## Pooled precision / recall & benign FP

| Metric | Value |
|--------|------:|
| TP | 102 |
| FN | 8 |
| FP (benign) | 0 |
| TN | 7 |
| Precision | 1.0000 |
| Recall | 0.9273 |
| Benign FP | 0 |
| Benign FP rate | 0.0000 |

_Detection rule: semantic rows only score as semantic when `semantic_verdict=detected`; structural rows only score exact-type when their own expected class is detected in preflight or exact-type async fallback._

## Results by conflict_class

| conflict_class | conflict_injected (log) | injection_failed (log) |
|----------------|-------------------------:|-----------------------:|
| `semantic_contradiction` | 40 | 1 |
| `dependency_impact` | 20 | 0 |
| `constraint_violation` | 20 | 0 |
| `temporal_invalidation` | 20 | 0 |
| `ambiguous_case` | 10 | 0 |
| **TOTAL** | **110** | **1** |

## Baseline simulation

Rule: baseline only flags **same-key overlapping validity** (Paper 3). Proposed facts use **p-*** keys, so `baseline_detectable` is **0** for all five classes; `baseline_missed` matches per-class row counts for this run.

Logged: `baseline_simulation` in `real_data_lab_execution_log.jsonl`; fact `research.rdl.baseline.simulation`.

## Missing baseline keys (preflight)

None logged.

## Failed corpus_row_id (if any)

`c-sem-09`

## Artifacts

- Execution log: `real-data-lab/research/real_data_lab_execution_log.jsonl`
- Checkpoints: `real-data-lab/research/real_data_lab_checkpoints.jsonl`
