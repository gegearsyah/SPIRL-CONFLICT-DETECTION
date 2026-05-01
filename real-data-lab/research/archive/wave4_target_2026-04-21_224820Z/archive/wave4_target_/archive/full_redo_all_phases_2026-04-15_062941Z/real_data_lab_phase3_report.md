# Phase 3 Report - Real Data Lab

Generated: 2026-04-14T20:07:30Z

- `project_id`: `918dccbb-ca79-42e8-9d74-15d99846975f`
- Architecture label: `predicate_routed_staged_embedding_nli`
- Architecture doc: `Spiral/docs/CONFLICT_DETECTION_ARCHITECTURE.md`
- Report status: `publishable`

## Mixed workload summary

| Metric | Value |
|--------|------:|
| Binary recall | 0.9636 |
| Core-4 exact-type recall | 0.7600 |
| All-row exact-type recall | 0.6909 |
| Wrong-type alert rate | 0.1909 |
| Benign FP rate | 0.1714 |
| Benign specificity | 0.8286 |
| Preflight coverage | 0.9636 |
| Preflight unavailable rate | 0.0364 |
| Semantic trace coverage | 1.0000 |
| Precision-safe mixed score | 0.4632 |

## Benign diagnostics

| Metric | Value |
|--------|------:|
| Semantic benign FP | 9 |
| Constraint benign FP | 3 |
| Dependency benign FP | 0 |
| Semantic budget-exhausted benign count | 2 |

## Coherence / authority summary

| Metric | Value |
|--------|------:|
| Preflight-first detected | 106 |
| Async-only recoveries | 0 |
| Preflight/async disagreements | 13 |
| Winning plane counts | `{"none": 106}` |
| Detector-plane authority | `nested_preflight_authority_when_available` |

## Report integrity

| Field | Value |
|-------|------:|
| Report integrity OK | `True` |
| Integrity notes | `none` |

## Contract audit

| Field | Value |
|-------|------:|
| Rows scored | 180 |
| Contract-complete rows | 180 |
| Contract-incomplete rows | 0 |
| Semantic trace missing | 0 |

## Benign FP by detector

| Detector | FP |
|----------|---:|
| `constraint_violation` | 3 |
| `semantic_contradiction` | 9 |

## Exact-type confusion matrix

| Expected | semantic | dependency | constraint | temporal | none |
|----------|---------:|-----------:|-----------:|---------:|-----:|
| `semantic_contradiction` | 28 | 5 | 5 | 2 | 0 |
| `dependency_impact` | 0 | 14 | 3 | 1 | 2 |
| `constraint_violation` | 0 | 0 | 19 | 0 | 1 |
| `temporal_invalidation` | 2 | 3 | 0 | 15 | 0 |
