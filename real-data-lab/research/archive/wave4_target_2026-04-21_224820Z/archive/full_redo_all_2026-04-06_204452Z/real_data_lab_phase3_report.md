# Phase 3 Report - Real Data Lab

Generated: 2026-04-06T18:25:32Z

- `project_id`: `0134d78e-4ac2-4cb4-8b7c-2c7693c79266`
- Architecture label: `predicate_routed_staged_embedding_nli`
- Architecture doc: `Spiral/docs/CONFLICT_DETECTION_ARCHITECTURE.md`
- Report status: `diagnostic_only`

## Mixed workload summary

| Metric | Value |
|--------|------:|
| Exact-type recall | 0.2727 |
| Wrong-type alert rate | 0.2636 |
| Benign specificity | 0.7250 |
| Preflight coverage | 0.0000 |
| Preflight unavailable rate | 0.0000 |
| Semantic trace coverage | 1.0000 |
| Precision-safe mixed score | 0.8514 |

## Contract audit

| Field | Value |
|-------|------:|
| Rows scored | 150 |
| Contract-complete rows | 80 |
| Contract-incomplete rows | 70 |
| Semantic trace missing | 0 |

## Benign FP by detector

| Detector | FP |
|----------|---:|
| `semantic_contradiction` | 11 |

## Exact-type confusion matrix

| Expected | semantic | dependency | constraint | temporal | none |
|----------|---------:|-----------:|-----------:|---------:|-----:|
| `semantic_contradiction` | 25 | 0 | 0 | 0 | 15 |
| `dependency_impact` | 8 | 0 | 0 | 0 | 12 |
| `constraint_violation` | 5 | 0 | 1 | 0 | 10 |
| `temporal_invalidation` | 10 | 0 | 0 | 4 | 4 |

This run is diagnostic-only because contract-critical fields were missing or semantic traces were incomplete.

