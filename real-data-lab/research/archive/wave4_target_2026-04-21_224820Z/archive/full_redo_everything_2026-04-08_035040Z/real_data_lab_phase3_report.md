# Phase 3 Report - Real Data Lab

Generated: 2026-04-07T21:26:14Z

- `project_id`: `e4b4cd05-1edf-4f38-b531-b3464af8b851`
- Architecture label: `predicate_routed_staged_embedding_nli`
- Architecture doc: `Spiral/docs/CONFLICT_DETECTION_ARCHITECTURE.md`
- Report status: `diagnostic_only`

## Mixed workload summary

| Metric | Value |
|--------|------:|
| Exact-type recall | 0.2727 |
| Wrong-type alert rate | 0.2455 |
| Benign specificity | 0.8000 |
| Preflight coverage | 0.0000 |
| Preflight unavailable rate | 0.0000 |
| Semantic trace coverage | 0.9667 |
| Precision-safe mixed score | 0.8082 |

## Contract audit

| Field | Value |
|-------|------:|
| Rows scored | 180 |
| Contract-complete rows | 67 |
| Contract-incomplete rows | 113 |
| Semantic trace missing | 6 |

## Benign FP by detector

| Detector | FP |
|----------|---:|
| `semantic_contradiction` | 14 |

## Exact-type confusion matrix

| Expected | semantic | dependency | constraint | temporal | none |
|----------|---------:|-----------:|-----------:|---------:|-----:|
| `semantic_contradiction` | 23 | 0 | 0 | 1 | 16 |
| `dependency_impact` | 8 | 1 | 0 | 0 | 11 |
| `constraint_violation` | 9 | 0 | 2 | 0 | 9 |
| `temporal_invalidation` | 9 | 0 | 0 | 4 | 7 |

This run is diagnostic-only because contract-critical fields were missing or semantic traces were incomplete.

