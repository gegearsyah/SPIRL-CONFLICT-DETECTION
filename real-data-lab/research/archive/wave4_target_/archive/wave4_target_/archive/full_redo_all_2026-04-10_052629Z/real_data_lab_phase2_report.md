# Phase 2 Report — Real Data Lab (Conflict injection)

Generated: 2026-04-09T20:11:46Z

## Corpus

- Source: `real-data-lab/list_conflict.md` (resolved: `C:\Users\GEYE ARDIANSYAH\Downloads\Innovation Hub\SPIRAL-RESEARCH\Beyond Temporal Contradiction\real-data-lab\list_conflict.md`)
- Mode: table-driven
- Project: `70baf95f-a31a-49f2-82dc-689937c105c3`
- Rows attempted: **110**
- Injection limit applied: **False**

## Results by conflict_class

| conflict_class | conflict_injected (log) | injection_failed (log) |
|----------------|-------------------------:|-----------------------:|
| `semantic_contradiction` | 40 | 0 |
| `dependency_impact` | 20 | 0 |
| `constraint_violation` | 20 | 0 |
| `temporal_invalidation` | 20 | 0 |
| `ambiguous_case` | 10 | 0 |
| **TOTAL** | **110** | **0** |

### Injection outcome notes

- **Successfully injected** (`conflict_injected`): **110**
- **Failed / not injected** (`injection_failed`, e.g. upsert error): **0**
- Detection metrics below apply only to rows that reached `conflict_injected` (c-* corpus ids).


## Conflict detection metrics (c-* corpus)

Derived from `phase==2`, `action==conflict_injected` lines for this `project_id` (same scoring rules as the mixed workload report).

| Metric | Value |
|--------|------:|
| Rows injected (c-*) | 110 |
| Binary detected (any alert) | 106 |
| Binary recall | 0.9636 |
| Exact-type detected | 83 |
| Exact-type recall | 0.7545 |
| Wrong-type alerts (cross-type) | 15 |
| Abstained rows (no alert) | 4 |

### Per-class detection

| conflict_class | injected | binary_detected | binary_recall | exact_detected | exact_recall | cross_type | abstained |
|----------------|---------:|----------------:|--------------:|---------------:|-------------:|-----------:|----------:|
| `semantic_contradiction` | 40 | 39 | 0.9750 | 37 | 0.9250 | 2 | 1 |
| `dependency_impact` | 20 | 19 | 0.9500 | 13 | 0.6500 | 6 | 1 |
| `constraint_violation` | 20 | 20 | 1.0000 | 18 | 0.9000 | 2 | 0 |
| `temporal_invalidation` | 20 | 20 | 1.0000 | 15 | 0.7500 | 5 | 0 |
| `ambiguous_case` | 10 | 8 | 0.8000 | 0 | 0.0000 | 0 | 2 |

### Detection verdict source (c-* rows)

| Source | Count |
|--------|------:|
| `preflight_exact` | 55 |
| `async_exact` | 28 |
| `preflight_cross_type` | 18 |
| `async_cross_type` | 5 |
| `none` | 4 |

## Benign slice in this log (b-* / sb-*)

| Metric | Value |
|--------|------:|
| Rows injected (benign IDs) | 8 |
| False positives | 0 |
| True negatives | 8 |
| FP rate | 0.0000 |

_If benign totals are zero, run Phase 2b (`real_data_lab_benign_mcp_run.py`) so pooled precision reflects false alerts on benign rows._

## Pooled binary (conflict = positive, benign = negative)

| Metric | Value |
|--------|------:|
| TP | 106 |
| FN | 4 |
| FP | 0 |
| TN | 8 |
| Precision | 1.0000 |
| Recall | 0.9636 |

## Exact-type precision (uses benign FP as exact-type false positives)

| Metric | Value |
|--------|------:|
| Exact TP | 83 |
| Exact FN | 27 |
| Precision | 1.0000 |
| Recall | 0.7545 |

## Exact-type confusion matrix (expected × predicted)

| Expected | semantic | dependency | constraint | temporal | ambig | none | other |
|----------|---------:|-----------:|-----------:|---------:|------:|-----:|------:|
| `semantic_contradiction` | 37 | 0 | 1 | 1 | 0 | 1 | 0 |
| `dependency_impact` | 4 | 13 | 2 | 0 | 0 | 1 | 0 |
| `constraint_violation` | 2 | 0 | 18 | 0 | 0 | 0 | 0 |
| `temporal_invalidation` | 3 | 2 | 0 | 15 | 0 | 0 | 0 |
| `ambiguous_case` | 5 | 0 | 2 | 1 | 0 | 2 | 0 |

_Detection rule: semantic rows only score as semantic when `semantic_verdict=detected` (or trace indicates emission); structural rows score exact-type when their expected class is detected in preflight or exact-type async fallback. Benign rows do not treat raw notification creation as truth when preflight verdict fields are present._

## Baseline simulation

Rule: baseline only flags **same-key overlapping validity** (Paper 3). Proposed facts use **p-*** keys, so `baseline_detectable` is **0** for all five classes; `baseline_missed` matches per-class row counts for this run.

Logged: `baseline_simulation` in `real_data_lab_execution_log.jsonl`; fact `research.rdl.baseline.simulation`.

## Missing baseline keys (preflight)

None logged.

## Failed corpus_row_id (if any)

None.

## Artifacts

- Execution log: `real-data-lab/research/real_data_lab_execution_log.jsonl`
- Checkpoints: `real-data-lab/research/real_data_lab_checkpoints.jsonl`
