# Phase 3 Report - Real Data Lab

Generated: 2026-04-24T18:56:33Z

- `project_id`: `1e9981eb-eaec-4689-8351-0611c3c12862`
- Architecture label: `predicate_routed_staged_embedding_nli`
- Architecture doc: `Spiral/docs/CONFLICT_DETECTION_ARCHITECTURE.md`
- Report status: `publishable`

## Mixed workload summary

| Metric | Value |
|--------|------:|
| Binary recall | 0.9727 |
| Core-4 exact-type recall | 0.7300 |
| All-row exact-type recall | 0.6636 |
| Wrong-type alert rate | 0.2182 |
| Benign FP rate | 0.0286 |
| Benign specificity | 0.9714 |
| Preflight coverage | 0.9818 |
| Preflight unavailable rate | 0.0182 |
| Semantic trace coverage | 1.0000 |
| Precision-safe mixed score | 0.5040 |

## Governance outcome (Wave 4.3)

Neyman-Pearson LLR selector (arXiv:2505.15008) promotes `governance_outcome` to a first-class preflight field and is scored here against the AbstentionBench (arXiv:2506.09038) protocol.

| Metric | Value |
|--------|------:|
| `needs_review` precision | 0.8000 |
| `needs_review` recall on ambiguous rows | 0.8000 |
| Unsafe forced-type rate (ambiguous) | 0.2000 |
| Ambiguous rows routed to `needs_review` (TP) | 8 |
| Benign rows routed to `needs_review` (FP) | 2 |
| Typed-conflict rows routed to `needs_review` (FN) | 70 |
| Governance outcome counts | `{"typed_conflict": 30, "needs_review": 80, "benign": 70, "unset": 0}` |

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
| Preflight-first detected | 107 |
| Async-only recoveries | 0 |
| Preflight/async disagreements | 17 |
| Winning plane counts | `{"governance_selector": 1, "semantic": 52, "structural": 55}` |
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
| `semantic_contradiction` | 29 | 4 | 4 | 3 | 0 |
| `dependency_impact` | 2 | 13 | 3 | 1 | 1 |
| `constraint_violation` | 1 | 0 | 18 | 0 | 1 |
| `temporal_invalidation` | 3 | 3 | 0 | 13 | 1 |
