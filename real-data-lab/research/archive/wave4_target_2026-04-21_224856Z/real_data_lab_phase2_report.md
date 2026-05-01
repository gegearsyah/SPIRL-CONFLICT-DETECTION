# Phase 2 Report — Real Data Lab (Conflict injection)

Generated: 2026-04-21T14:29:04Z

Project: `ba546025-9c6f-438a-a661-89500d6bec7a`

## Corpus

- Source: `real-data-lab/list_conflict.md` (resolved: `C:\Users\GEYE ARDIANSYAH\Downloads\Innovation Hub\SPIRAL-RESEARCH\Beyond Temporal Contradiction\real-data-lab\list_conflict.md`)
- Mode: table-driven
- Rows attempted: **110**
- Injection limit applied: **False**

## Pre-injection seed audit (last logged)

- Manifest: `C:\Users\GEYE ARDIANSYAH\Downloads\Innovation Hub\SPIRAL-RESEARCH\Beyond Temporal Contradiction\real-data-lab\Project Core Platform.skf.json`
- Expected seeded corpus facts (SKF): **79**
- Total facts listed at audit: **81**
- SKF keys missing in project: **0**
- Sample manifest key resolved: `f-api-02`

## Conflicts (c-* corpus) — injection-time detector surface

Metrics below are derived from `conflict_injected` log lines for agent `rdl_phase2_seed_agent` (same detection scoring as the mixed report conflict block).

The current live conflict-injection surface is strongest on constraint, strong on temporal, respectable on dependency and semantic, and still pending a benign-only readout before precision and F1 are finalized.

| Metric | Value |
|--------|------:|
| Rows (log slice, c-*) | 110 |
| Rows (core-4, non-ambiguous) | 100 |
| Binary detected (any alert) | 109 |
| Binary recall | 0.9909 |
| Exact-type matches (core-4) | 78 |
| Core-4 exact-type recall | 0.7800 |
| All-row exact-type recall | 0.7091 |
| Cross-type alerts | 21 |
| Abstained rows | 1 |
| Benign status | TBD |

- Preflight-first detected rows: **108**
- Preflight/async disagreements: **14**
- Async-only recoveries: **1**

## Ambiguous rows

- Ambiguous rows total: **10**
- Ambiguous alerted: **10**
- Ambiguous abstained: **0**
- Unsafe forced-type rate: **1.0000**

_Ambiguous rows are excluded from the **core-4 exact-type headline metric** and reported separately as handling quality._

## Per-class detection (injection-time)

| conflict_class | rows (log slice) | binary alert | exact-type match | cross-type | abstained |
|----------------|-----------------:|-------------:|-----------------:|-----------:|----------:|
| `semantic_contradiction` | 40 | 40 | 30 | 10 | 0 |
| `dependency_impact` | 20 | 20 | 14 | 6 | 0 |
| `constraint_violation` | 20 | 20 | 19 | 1 | 0 |
| `temporal_invalidation` | 20 | 19 | 15 | 4 | 1 |
| `ambiguous_case` | 10 | 10 | 0 | 0 | 0 |

## Primary detector source (first matching signal)

| primary_detector_source | rows |
|--------------------------|-----:|
| `preflight_first_structural_exact` | 40 |
| `preflight_first_semantic_exact` | 37 |
| `preflight_first_structural_cross_type` | 19 |
| `preflight_first_semantic_cross_type` | 12 |
| `async_exact` | 1 |
| `none` | 1 |

## Winning plane / cross-type pressure

- Winning plane counts: `{"semantic": 49, "structural": 59}`
- Cross-type alerts by winning plane: `{"structural": 15, "semantic": 6}`

_Note: the bucket key `none` means the flattened row contract still carried a missing, null, or literal `"none"` `winning_detector_plane`. It is a **logging/flattening artifact**, not proof the detector used no plane. When nested preflight values are present, those are the authoritative detector-plane values. **Exact-type scoring is driven by predicted vs expected conflict type, not by this histogram.**_

## Row evaluation contract (first row sample)

| Field | Value |
|-------|-------|
| Evaluation contract | `rdl-eval-2026-04-05-v1` |
| Detector bundle | `semantic_current+dependency_v3+constraint_v2+temporal_v3+w4_governance_v1` |
| Config fingerprint | `e97787bed902bfd9` |

## Row contract / outcome_class tallies (log slice)

- `row_contract_complete: true`: **110**
- `row_contract_complete: false`: **0**

| outcome_class (logged) | rows |
|-------------------------|-----:|
| `detected` | 108 |
| `abstain` | 2 |

## Exact-type confusion matrix (structural + semantic columns)

| Expected | semantic | dependency | constraint | temporal | none |
|----------|---------:|-----------:|-----------:|---------:|-----:|
| `semantic_contradiction` | 30 | 4 | 4 | 2 | 0 |
| `dependency_impact` | 2 | 14 | 3 | 1 | 0 |
| `constraint_violation` | 1 | 0 | 19 | 0 | 0 |
| `temporal_invalidation` | 1 | 3 | 0 | 15 | 1 |

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

Rule: baseline only flags **same-key overlapping validity**. Proposed facts use **p-*** keys, so `baseline_detectable` is **0** for all five classes; `baseline_missed` matches per-class row counts for this run.

Logged: `baseline_simulation` in `real_data_lab_execution_log.jsonl`; fact `research.rdl.baseline.simulation`.

## Missing baseline keys (preflight)

None logged.

## Failed corpus_row_id (if any)

None.

## Artifacts

- Execution log: `real-data-lab/research/real_data_lab_execution_log.jsonl`
- Checkpoints: `real-data-lab/research/real_data_lab_checkpoints.jsonl`
