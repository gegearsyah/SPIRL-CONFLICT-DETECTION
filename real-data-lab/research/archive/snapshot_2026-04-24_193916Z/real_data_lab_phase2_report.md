# Phase 2 Report — Real Data Lab (Conflict injection)

Generated: 2026-04-24T02:42:19Z

Project: `67c79754-e9d4-45a2-8ebe-d4c4c730c83b`

## Corpus

- Source: `real-data-lab/list_conflict.md` (resolved: `C:\Users\GEYE ARDIANSYAH\Downloads\Innovation Hub\SPIRAL-RESEARCH\Beyond Temporal Contradiction\real-data-lab\list_conflict.md`)
- Mode: table-driven
- Rows attempted: **110**
- Injection limit applied: **False**

## Pre-injection seed audit (last logged)

- Manifest: `C:\Users\GEYE ARDIANSYAH\Downloads\Innovation Hub\SPIRAL-RESEARCH\Beyond Temporal Contradiction\real-data-lab\Project Core Platform.skf.json`
- Expected seeded corpus facts (SKF): **79**
- Total facts listed at audit: **445**
- SKF keys missing in project: **0**
- Sample manifest key resolved: `f-api-02`

## Conflicts (c-* corpus) — injection-time detector surface

Metrics below are derived from `conflict_injected` log lines for agent `rdl_phase2_seed_agent` (same detection scoring as the mixed report conflict block).

The current live conflict-injection surface is strongest on constraint, strong on temporal, respectable on dependency and semantic, and still pending a benign-only readout before precision and F1 are finalized.

| Metric | Value |
|--------|------:|
| Rows (log slice, c-*) | 110 |
| Rows (core-4, non-ambiguous) | 100 |
| Binary detected (any alert) | 106 |
| Binary recall | 0.9636 |
| Exact-type matches (core-4) | 74 |
| Core-4 exact-type recall | 0.7400 |
| All-row exact-type recall | 0.6727 |
| Cross-type alerts | 23 |
| Abstained rows | 4 |
| Benign status | TBD |

- Preflight-first detected rows: **106**
- Preflight/async disagreements: **17**
- Async-only recoveries: **0**

## Ambiguous rows

- Ambiguous rows total: **10**
- Ambiguous alerted: **9**
- Ambiguous abstained: **1**
- Ambiguous routed to review (governance needs_review): **9** (0.9000)
- Unsafe forced-type rate: **0.0000** (governance-aware, contract `rdl-eval-2026-04-23-v2`)
- Governance outcome counts: `{"needs_review": 107, "benign": 2, "typed_conflict": 1}`

_Ambiguous rows are excluded from the **core-4 exact-type headline metric** and reported separately as handling quality._
_Unsafe forced-type rate is governance-aware: typed alerts that were routed to ``needs_review`` by the Neyman-Pearson governance selector (Wave 4.3) are NOT counted as forced — they are the intended deferral path (Chow 1970; Madras et al. 2018; Mozannar & Sontag 2020)._

## Per-class detection (injection-time)

| conflict_class | rows (log slice) | binary alert | exact-type match | cross-type | abstained |
|----------------|-----------------:|-------------:|-----------------:|-----------:|----------:|
| `semantic_contradiction` | 40 | 39 | 29 | 10 | 1 |
| `dependency_impact` | 20 | 20 | 14 | 6 | 0 |
| `constraint_violation` | 20 | 19 | 18 | 1 | 1 |
| `temporal_invalidation` | 20 | 19 | 13 | 6 | 1 |
| `ambiguous_case` | 10 | 9 | 0 | 0 | 1 |

## Primary detector source (first matching signal)

| primary_detector_source | rows |
|--------------------------|-----:|
| `preflight_first_semantic_exact` | 37 |
| `preflight_first_structural_exact` | 37 |
| `preflight_first_structural_cross_type` | 18 |
| `preflight_first_semantic_cross_type` | 14 |
| `preflight_abstain` | 2 |
| `none` | 2 |

## Winning plane / cross-type pressure

- Winning plane counts: `{"semantic": 51, "structural": 55, "governance_selector": 2}`
- Cross-type alerts by winning plane: `{"structural": 15, "semantic": 8}`

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
| `semantic_contradiction` | 29 | 4 | 4 | 2 | 1 |
| `dependency_impact` | 2 | 14 | 3 | 1 | 0 |
| `constraint_violation` | 1 | 0 | 18 | 0 | 1 |
| `temporal_invalidation` | 3 | 3 | 0 | 13 | 1 |

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
