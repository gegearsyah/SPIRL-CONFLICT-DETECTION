# Mixed workload report - Real Data Lab (conflicts + benign)

Generated: 2026-04-21T21:08:34Z

Project: `ba546025-9c6f-438a-a661-89500d6bec7a`

The detector currently looks strongest on constraint, strong on temporal, and respectable on dependency and semantic. The main remaining blocker is benign precision, so this report now separates core typed conflict routing from ambiguous-case handling and bounded report-integrity checks.

## Conflicts (c-* corpus, `real-data-lab/list_conflict.md`)

| Metric | Value |
|--------|------:|
| Rows (all conflict rows) | 110 |
| Rows (core-4 only) | 100 |
| Binary detected (any alert) | 109 |
| Binary recall | 0.9909 |
| Core-4 exact-type recall | 0.7800 |
| All-row exact-type recall | 0.7091 |
| Cross-type alerts | 21 |
| Abstained rows | 1 |
| Preflight-first detected | 108 |
| Preflight/async disagreements | 14 |
| Async-only recoveries | 1 |

## Ambiguous rows

| Metric | Value |
|--------|------:|
| Ambiguous rows total | 10 |
| Ambiguous alerted | 10 |
| Ambiguous abstained | 0 |
| Unsafe forced-type rate | 1.0000 |

_Ambiguous rows are tracked separately and excluded from the core-4 headline exact-type metric._

## Benign (b-* / sb-* corpus, `real-data-lab/list_benign.md`)

| Metric | Value |
|--------|------:|
| Rows (injected, benign IDs) | 70 |
| False positives | 2 |
| True negatives | 68 |
| FP rate | 0.0286 |
| Specificity | 0.9714 |
| Semantic benign FP | 0 |
| Constraint benign FP | 1 |
| Dependency benign FP | 1 |
| Semantic budget-exhausted benign count | 1 |

## Benign FP by detector

| Detector | Benign FP |
|----------|----------:|
| `constraint_violation` | 1 |
| `dependency_impact` | 1 |

## Pooled binary: alert warranted (conflict = positive, benign = negative)

| Metric | Value |
|--------|------:|
| TP | 109 |
| FN | 1 |
| FP | 2 |
| TN | 68 |
| Precision | 0.9820 |
| Recall | 0.9909 |
| Wrong-type alert rate | 0.1909 |
| Preflight coverage | 0.9818 |
| Preflight unavailable rate | 0.0182 |
| Semantic trace coverage | 1.0000 |
| Precision-safe mixed score | 0.5573 |

## Report integrity

| Metric | Value |
|--------|------:|
| Report integrity OK | `True` |
| Rows scored | 180 |
| Detector-plane authority | `nested_preflight_authority_when_available` |
| Integrity notes | `none` |

## Exact-type confusion matrix

| Expected | semantic | dependency | constraint | temporal | none |
|----------|---------:|-----------:|-----------:|---------:|-----:|
| `semantic_contradiction` | 30 | 4 | 4 | 2 | 0 |
| `dependency_impact` | 2 | 14 | 3 | 1 | 0 |
| `constraint_violation` | 1 | 0 | 19 | 0 | 0 |
| `temporal_invalidation` | 1 | 3 | 0 | 15 | 1 |

_Detection rule: preflight `final_conflict_type` is authoritative when present. Mixed-report exact-type scoring uses the same derived predicted type for confusion, benign FP accounting, and detector-level breakdowns._
