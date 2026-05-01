# Phase 3 Report - Real Data Lab

Generated: 2026-04-24T08:21:15Z

- `project_id`: `67c79754-e9d4-45a2-8ebe-d4c4c730c83b`
- Architecture label: `predicate_routed_staged_embedding_nli`
- Architecture doc: `Spiral/docs/CONFLICT_DETECTION_ARCHITECTURE.md`
- Report status: `publishable`

## Mixed workload summary

| Metric | Value |
|--------|------:|
| Binary recall | 0.9636 |
| Core-4 exact-type recall | 0.7400 |
| All-row exact-type recall | 0.6727 |
| Wrong-type alert rate | 0.2091 |
| Benign FP rate | 0.0286 |
| Benign specificity | 0.9714 |
| Preflight coverage | 0.9818 |
| Preflight unavailable rate | 0.0182 |
| Semantic trace coverage | 1.0000 |
| Precision-safe mixed score | 0.5169 |

## Governance outcome (Wave 4.3)

Neyman-Pearson LLR selector (arXiv:2505.15008) promotes `governance_outcome` to a first-class preflight field and is scored here against the AbstentionBench (arXiv:2506.09038) protocol.

| Metric | Value |
|--------|------:|
| `needs_review` precision | 0.4091 |
| `needs_review` recall on ambiguous rows | 0.9000 |
| Unsafe forced-type rate (ambiguous) | 0.0000 |
| Ambiguous rows routed to `needs_review` (TP) | 9 |
| Benign rows routed to `needs_review` (FP) | 13 |
| Typed-conflict rows routed to `needs_review` (FN) | 98 |
| Governance outcome counts | `{"typed_conflict": 1, "needs_review": 120, "benign": 59, "unset": 0}` |

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
| Preflight-first detected | 106 |
| Async-only recoveries | 0 |
| Preflight/async disagreements | 17 |
| Winning plane counts | `{"governance_selector": 2, "semantic": 51, "structural": 55}` |
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
| `semantic_contradiction` | 29 | 4 | 4 | 2 | 1 |
| `dependency_impact` | 2 | 14 | 3 | 1 | 0 |
| `constraint_violation` | 1 | 0 | 18 | 0 | 1 |
| `temporal_invalidation` | 3 | 3 | 0 | 13 | 1 |
