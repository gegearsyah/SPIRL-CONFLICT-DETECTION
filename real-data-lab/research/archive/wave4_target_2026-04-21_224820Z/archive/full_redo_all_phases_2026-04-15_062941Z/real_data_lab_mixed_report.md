# Mixed workload report - Real Data Lab (conflicts + benign)

Generated: 2026-04-14T20:07:30Z

Project: `918dccbb-ca79-42e8-9d74-15d99846975f`

The detector currently looks strongest on constraint, strong on temporal, and respectable on dependency and semantic. The main remaining blocker is benign precision, so this report now separates core typed conflict routing from ambiguous-case handling and bounded report-integrity checks.

## Conflicts (c-* corpus, `real-data-lab/list_conflict.md`)

| Metric | Value |
|--------|------:|
| Rows (all conflict rows) | 110 |
| Rows (core-4 only) | 100 |
| Binary detected (any alert) | 106 |
| Binary recall | 0.9636 |
| Core-4 exact-type recall | 0.7600 |
| All-row exact-type recall | 0.6909 |
| Cross-type alerts | 21 |
| Abstained rows | 4 |
| Preflight-first detected | 106 |
| Preflight/async disagreements | 13 |
| Async-only recoveries | 0 |

## Ambiguous rows

| Metric | Value |
|--------|------:|
| Ambiguous rows total | 10 |
| Ambiguous alerted | 9 |
| Ambiguous abstained | 1 |
| Unsafe forced-type rate | 0.9000 |

_Ambiguous rows are tracked separately and excluded from the core-4 headline exact-type metric._

## Benign (b-* / sb-* corpus, `real-data-lab/list_benign.md`)

| Metric | Value |
|--------|------:|
| Rows (injected, benign IDs) | 70 |
| False positives | 12 |
| True negatives | 58 |
| FP rate | 0.1714 |
| Specificity | 0.8286 |
| Semantic benign FP | 9 |
| Constraint benign FP | 3 |
| Dependency benign FP | 0 |
| Semantic budget-exhausted benign count | 2 |

## Benign FP by detector

| Detector | Benign FP |
|----------|----------:|
| `constraint_violation` | 3 |
| `semantic_contradiction` | 9 |

## Pooled binary: alert warranted (conflict = positive, benign = negative)

| Metric | Value |
|--------|------:|
| TP | 106 |
| FN | 4 |
| FP | 12 |
| TN | 58 |
| Precision | 0.8983 |
| Recall | 0.9636 |
| Wrong-type alert rate | 0.1909 |
| Preflight coverage | 0.9636 |
| Preflight unavailable rate | 0.0364 |
| Semantic trace coverage | 1.0000 |
| Precision-safe mixed score | 0.4632 |

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
| `semantic_contradiction` | 28 | 5 | 5 | 2 | 0 |
| `dependency_impact` | 0 | 14 | 3 | 1 | 2 |
| `constraint_violation` | 0 | 0 | 19 | 0 | 1 |
| `temporal_invalidation` | 2 | 3 | 0 | 15 | 0 |

_Detection rule: preflight `final_conflict_type` is authoritative when present. Mixed-report exact-type scoring uses the same derived predicted type for confusion, benign FP accounting, and detector-level breakdowns._
