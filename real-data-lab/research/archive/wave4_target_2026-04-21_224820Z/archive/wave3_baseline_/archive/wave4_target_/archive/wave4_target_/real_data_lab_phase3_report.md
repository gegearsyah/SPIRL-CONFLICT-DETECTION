# Phase 3 Report - Real Data Lab

Generated: 2026-04-16T01:08:31Z

- `project_id`: `e1c86cae-2dba-4298-a65e-e55609d31570`
- Architecture label: `predicate_routed_staged_embedding_nli`
- Architecture doc: `Spiral/docs/CONFLICT_DETECTION_ARCHITECTURE.md`
- Report status: `publishable`

## Mixed workload summary

| Metric | Value |
|--------|------:|
| Binary recall | 0.9818 |
| Core-4 exact-type recall | 0.7800 |
| All-row exact-type recall | 0.7091 |
| Wrong-type alert rate | 0.1818 |
| Benign FP rate | 0.0286 |
| Benign specificity | 0.9714 |
| Preflight coverage | 0.9818 |
| Preflight unavailable rate | 0.0182 |
| Semantic trace coverage | 1.0000 |
| Precision-safe mixed score | 0.5636 |

## Benign diagnostics

| Metric | Value |
|--------|------:|
| Semantic benign FP | 1 |
| Constraint benign FP | 0 |
| Dependency benign FP | 1 |
| Semantic budget-exhausted benign count | 0 |

## Coherence / authority summary

| Metric | Value |
|--------|------:|
| Preflight-first detected | 108 |
| Async-only recoveries | 0 |
| Preflight/async disagreements | 10 |
| Winning plane counts | `{"semantic": 51, "structural": 57}` |
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
| `dependency_impact` | 1 |
| `semantic_contradiction` | 1 |

## Exact-type confusion matrix

| Expected | semantic | dependency | constraint | temporal | none |
|----------|---------:|-----------:|-----------:|---------:|-----:|
| `semantic_contradiction` | 31 | 5 | 4 | 0 | 0 |
| `dependency_impact` | 1 | 16 | 2 | 1 | 0 |
| `constraint_violation` | 1 | 0 | 18 | 0 | 1 |
| `temporal_invalidation` | 3 | 3 | 0 | 13 | 1 |
