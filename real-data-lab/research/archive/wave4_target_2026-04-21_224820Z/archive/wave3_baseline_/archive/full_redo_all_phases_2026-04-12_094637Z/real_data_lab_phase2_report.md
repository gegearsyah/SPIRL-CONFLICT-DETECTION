# Phase 2 Report — Real Data Lab (Conflict injection)

Generated: 2026-04-12T05:53:47Z

Project: `39108fb6-1ad9-4139-9a47-93aeb3aa8436`

## Corpus

- Source: `real-data-lab/list_conflict.md` (resolved: `C:\Users\GEYE ARDIANSYAH\Downloads\Innovation Hub\SPIRAL-RESEARCH\Beyond Temporal Contradiction\real-data-lab\list_conflict.md`)
- Mode: table-driven
- Rows attempted: **110**
- Injection limit applied: **False**

## Pre-injection seed audit (last logged)

- Manifest: `C:\Users\GEYE ARDIANSYAH\Downloads\Innovation Hub\SPIRAL-RESEARCH\Beyond Temporal Contradiction\real-data-lab\Project Core Platform.skf.json`
- Expected seeded corpus facts (SKF): **79**
- Total facts listed at audit: **219**
- SKF keys missing in project: **0**
- Sample manifest key resolved: `f-api-02`

## Conflicts (c-* corpus) — injection-time detector surface

Metrics below are derived from `conflict_injected` log lines for agent `rdl_phase2_seed_agent` (same detection scoring as the mixed report conflict block).

| Metric | Value |
|--------|------:|
| Rows (log slice, c-*) | 110 |
| Binary detected (any alert) | 102 |
| Binary recall | 0.9273 |
| Exact-type detected | 61 |
| Exact-type recall | 0.5545 |
| Cross-type alerts | 34 |
| Abstained rows | 8 |

## Per-class detection (injection-time)

| conflict_class | rows (log slice) | binary alert | exact-type match | cross-type | abstained |
|----------------|-----------------:|-------------:|-----------------:|-----------:|----------:|
| `semantic_contradiction` | 40 | 39 | 23 | 16 | 1 |
| `dependency_impact` | 20 | 18 | 12 | 6 | 2 |
| `constraint_violation` | 20 | 18 | 17 | 1 | 2 |
| `temporal_invalidation` | 20 | 20 | 9 | 11 | 0 |
| `ambiguous_case` | 10 | 7 | 0 | 0 | 3 |

## Primary detector source (first matching signal)

| primary_detector_source | rows |
|--------------------------|-----:|
| `async_exact` | 61 |
| `async_cross_type` | 41 |
| `none` | 8 |

## Row evaluation contract (first row sample)

| Field | Value |
|-------|-------|
| Evaluation contract | `rdl-eval-2026-04-05-v1` |
| Detector bundle | `semantic_current+dependency_v2+constraint_v2+temporal_v2` |
| Config fingerprint | `2945a5e6b9072e66` |

## Row contract / outcome_class tallies (log slice)

- `row_contract_complete: true`: **70**
- `row_contract_complete: false`: **40**

| outcome_class (logged) | rows |
|-------------------------|-----:|
| `unavailable` | 110 |

## Exact-type confusion matrix (structural + semantic columns)

| Expected | semantic | dependency | constraint | temporal | none |
|----------|---------:|-----------:|-----------:|---------:|-----:|
| `semantic_contradiction` | 23 | 13 | 1 | 2 | 1 |
| `dependency_impact` | 5 | 12 | 0 | 1 | 2 |
| `constraint_violation` | 0 | 0 | 17 | 0 | 2 |
| `temporal_invalidation` | 4 | 7 | 0 | 9 | 0 |

_Detection rule: semantic rows only score as semantic when `semantic_verdict=detected` (or semantic trace shows an emitted contradiction); structural rows score exact-type when the expected class appears in preflight, inline preflight, or async notification._

## Results by conflict_class (injection accounting)

| conflict_class | conflict_injected (log) | injection_failed (log) |
|----------------|-------------------------:|-----------------------:|
| `semantic_contradiction` | 40 | 0 |
| `dependency_impact` | 20 | 0 |
| `constraint_violation` | 20 | 0 |
| `temporal_invalidation` | 20 | 0 |
| `ambiguous_case` | 10 | 0 |
| **TOTAL** | **110** | **0** |

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
