# Phase 3 Report - Real Data Lab

Generated: 2026-04-10T03:41:09Z

- `project_id`: `70baf95f-a31a-49f2-82dc-689937c105c3`
- Architecture label: `predicate_routed_staged_embedding_nli`
- Architecture doc: `Spiral/docs/CONFLICT_DETECTION_ARCHITECTURE.md`
- Report status: `diagnostic_only`

## Mixed workload summary

| Metric | Value |
|--------|------:|
| Exact-type recall | 0.7545 |
| Wrong-type alert rate | 0.1364 |
| Benign specificity | 0.7000 |
| Preflight coverage | 0.0000 |
| Preflight unavailable rate | 0.0000 |
| Semantic trace coverage | 0.0000 |
| Precision-safe mixed score | 0.8043 |

## Contract audit

| Field | Value |
|-------|------:|
| Rows scored | 0 |
| Contract-complete rows | 0 |
| Contract-incomplete rows | 0 |
| Semantic trace missing | 0 |

## Benign FP by detector

| Detector | FP |
|----------|---:|
| `constraint_violation` | 7 |
| `semantic_contradiction` | 14 |

## Exact-type confusion matrix

| Expected | semantic | dependency | constraint | temporal | none |
|----------|---------:|-----------:|-----------:|---------:|-----:|
| `semantic_contradiction` | 37 | 0 | 1 | 1 | 1 |
| `dependency_impact` | 4 | 13 | 2 | 0 | 1 |
| `constraint_violation` | 2 | 0 | 18 | 0 | 0 |
| `temporal_invalidation` | 3 | 2 | 0 | 15 | 0 |

This run is diagnostic-only because contract-critical fields were missing or semantic traces were incomplete.

