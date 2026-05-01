# Phase 3 Report - Real Data Lab

Generated: 2026-04-21T21:08:36Z

- `project_id`: `ba546025-9c6f-438a-a661-89500d6bec7a`
- Architecture label: `predicate_routed_staged_embedding_nli`
- Architecture doc: `Spiral/docs/CONFLICT_DETECTION_ARCHITECTURE.md`
- Report status: `publishable`

## Mixed workload summary

| Metric | Value |
|--------|------:|
| Binary recall | 0.9909 |
| Core-4 exact-type recall | 0.7800 |
| All-row exact-type recall | 0.7091 |
| Wrong-type alert rate | 0.1909 |
| Benign FP rate | 0.0286 |
| Benign specificity | 0.9714 |
| Preflight coverage | 0.9818 |
| Preflight unavailable rate | 0.0182 |
| Semantic trace coverage | 1.0000 |
| Precision-safe mixed score | 0.5573 |

## Governance outcome (Wave 4.3)

Neyman-Pearson LLR selector (arXiv:2505.15008) promotes `governance_outcome` to a first-class preflight field and is scored here against the AbstentionBench (arXiv:2506.09038) protocol.

| Metric | Value |
|--------|------:|
| `needs_review` precision | 0.0000 |
| `needs_review` recall on ambiguous rows | 0.0000 |
| Unsafe forced-type rate (ambiguous) | 1.0000 |
| Ambiguous rows routed to `needs_review` (TP) | 0 |
| Benign rows routed to `needs_review` (FP) | 0 |
| Typed-conflict rows routed to `needs_review` (FN) | 0 |
| Governance outcome counts | `{"typed_conflict": 0, "needs_review": 0, "benign": 0, "unset": 180}` |

## Benign diagnostics

| Metric | Value |
|--------|------:|
| Semantic benign FP | 0 |
| Constraint benign FP | 1 |
| Dependency benign FP | 1 |
| Semantic budget-exhausted benign count | 1 |

## Coherence / authority summary

| Metric | Value |
|--------|------:|
| Preflight-first detected | 108 |
| Async-only recoveries | 1 |
| Preflight/async disagreements | 14 |
| Winning plane counts | `{"semantic": 49, "structural": 59}` |
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
| `constraint_violation` | 1 |
| `dependency_impact` | 1 |

## Exact-type confusion matrix

| Expected | semantic | dependency | constraint | temporal | none |
|----------|---------:|-----------:|-----------:|---------:|-----:|
| `semantic_contradiction` | 30 | 4 | 4 | 2 | 0 |
| `dependency_impact` | 2 | 14 | 3 | 1 | 0 |
| `constraint_violation` | 1 | 0 | 19 | 0 | 0 |
| `temporal_invalidation` | 1 | 3 | 0 | 15 | 1 |
