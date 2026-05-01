# Phase 2 Report — Real Data Lab (Conflict injection)

Generated: 2026-04-11T11:39:48Z

Project: `63aa1d80-6928-4ed7-82ec-afdc2cc8a2f7`

## Corpus

- Source: `real-data-lab/list_conflict.md` (resolved: `C:\Users\GEYE ARDIANSYAH\Downloads\Innovation Hub\SPIRAL-RESEARCH\Beyond Temporal Contradiction\real-data-lab\list_conflict.md`)
- Benign table (Phase 2b; metrics below include b-* only after that phase): `real-data-lab/list_benign.md`
- Mode: table-driven
- Rows attempted: **110**
- Injection limit applied: **False**

## Injection counts by conflict_class (upsert outcome)

| conflict_class | conflict_injected (log) | injection_failed (log) |
|----------------|-------------------------:|-----------------------:|
| `semantic_contradiction` | 40 | 0 |
| `dependency_impact` | 20 | 0 |
| `constraint_violation` | 20 | 0 |
| `temporal_invalidation` | 20 | 0 |
| `ambiguous_case` | 10 | 0 |
| **TOTAL** | **110** | **0** |

## Detection metrics (from `conflict_injected` log; same layout as mixed report)

_Conflict rows are corpus ids `c-*`. After Phase 2b, benign `b-*` / `sb-*` rows appear in the same log; metrics in this section are recomputed from the log and scoped to this **project** when present._

## Conflicts (c-* corpus, `real-data-lab/list_conflict.md`)

| Metric | Value |
|--------|------:|
| Rows (injected, c-*) | 110 |
| Binary detected (any alert) | 102 |
| Binary recall | 0.9273 |
| Exact-type detected | 76 |
| Exact-type recall | 0.6909 |
| Cross-type alerts | 17 |
| Abstained rows | 8 |

## Per-class breakdown (c-* rows, from execution log)

| conflict_class | injected | binary_detected | exact_detected | cross_type_alerts | abstained |
|----------------|---------:|----------------:|---------------:|------------------:|------------:|
| `semantic_contradiction` | 40 | 39 | 39 | 0 | 1 |
| `dependency_impact` | 20 | 18 | 10 | 8 | 2 |
| `constraint_violation` | 20 | 16 | 15 | 1 | 4 |
| `temporal_invalidation` | 20 | 20 | 12 | 8 | 0 |
| `ambiguous_case` | 10 | 9 | 0 | 0 | 1 |

## Benign (b-* / sb-* corpus, `real-data-lab/list_benign.md`)

| Metric | Value |
|--------|------:|
| Rows (injected, benign IDs) | 41 |
| False positives | 2 |
| True negatives | 39 |
| FP rate | 0.0488 |

## Preflight / async coherence

| Metric | Value |
|--------|------:|
| Disagreement rows | 57 |
| Async stronger than preflight | 0 |
| Async-only benign FP | 0 |
| Conflict rows recovered async | 0 |
| Preflight-rejected but async-detected | 56 |

## Detector coherence mix

| Coherence | Rows |
|-----------|-----:|
| `coherent` | 42 |
| `disagreement` | 57 |
| `none` | 47 |
| `preflight_only` | 5 |

## Benign FP by detector

| Detector | Benign FP |
|----------|----------:|
| `semantic_contradiction` | 2 |

## Pooled binary: alert warranted (conflict = positive, benign = negative)

| Metric | Value |
|--------|------:|
| TP | 102 |
| FN | 8 |
| FP | 2 |
| TN | 39 |
| Precision | 0.9808 |
| Recall | 0.9273 |

## Exact-type confusion matrix

| Expected | semantic | dependency | constraint | temporal | none |
|----------|---------:|-----------:|-----------:|---------:|-----:|
| `semantic_contradiction` | 39 | 0 | 0 | 0 | 1 |
| `dependency_impact` | 8 | 10 | 0 | 0 | 2 |
| `constraint_violation` | 1 | 0 | 15 | 0 | 4 |
| `temporal_invalidation` | 8 | 0 | 0 | 12 | 0 |

_Detection rule: semantic rows only score as semantic when `semantic_verdict=detected`; structural rows only score exact-type when their own expected class is detected in preflight or exact-type async fallback. Benign rows do not treat raw notification creation as truth when preflight verdict fields are present._

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
