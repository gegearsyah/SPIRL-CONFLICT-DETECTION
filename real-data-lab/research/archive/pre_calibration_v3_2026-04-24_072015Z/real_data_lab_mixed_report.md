# Mixed workload report - Real Data Lab (conflicts + benign)

Generated: 2026-04-23T20:59:34Z

Project: `67c79754-e9d4-45a2-8ebe-d4c4c730c83b`

The detector currently looks strongest on constraint, strong on temporal, and respectable on dependency and semantic. The main remaining blocker is benign precision, so this report now separates core typed conflict routing from ambiguous-case handling and bounded report-integrity checks.

## Conflicts (c-* corpus, `real-data-lab/list_conflict.md`)

| Metric | Value |
|--------|------:|
| Rows (all conflict rows) | 110 |
| Rows (core-4 only) | 100 |
| Binary detected (any alert) | 107 |
| Binary recall | 0.9727 |
| Core-4 exact-type recall | 0.7600 |
| All-row exact-type recall | 0.6909 |
| Cross-type alerts | 21 |
| Abstained rows | 3 |
| Preflight-first detected | 107 |
| Preflight/async disagreements | 18 |
| Async-only recoveries | 0 |

## Ambiguous rows

| Metric | Value |
|--------|------:|
| Ambiguous rows total | 10 |
| Ambiguous alerted | 10 |
| Ambiguous abstained | 0 |
| Ambiguous routed to needs_review | 10 / 10 |
| Unsafe forced-type rate (ambiguous) | 0.0000 |
| Governance outcome counts | `{"typed_conflict": 2, "needs_review": 120, "benign": 58, "unset": 0}` |

_Ambiguous rows are tracked separately and excluded from the core-4 headline exact-type metric._

_Unsafe forced-type rate is governance-aware (Wave 4.3+; evaluation_contract_version=`rdl-eval-2026-04-23-v2`). Rows routed by the Neyman-Pearson governance selector to ``needs_review`` are the intended deferral path (Chow 1970 IEEE TIT; Madras, Pitassi & Zemel NeurIPS 2018; AbstentionBench arXiv:2506.09038) and are NOT counted as forced-type errors._

## Benign (b-* / sb-* corpus, `real-data-lab/list_benign.md`)

| Metric | Value |
|--------|------:|
| Rows (injected, benign IDs) | 70 |
| False positives | 1 |
| True negatives | 69 |
| FP rate | 0.0143 |
| Specificity | 0.9857 |
| Semantic benign FP | 0 |
| Constraint benign FP | 0 |
| Dependency benign FP | 1 |
| Semantic budget-exhausted benign count | 0 |

## Benign FP by detector

| Detector | Benign FP |
|----------|----------:|
| `dependency_impact` | 1 |

## Pooled binary: alert warranted (conflict = positive, benign = negative)

| Metric | Value |
|--------|------:|
| TP | 107 |
| FN | 3 |
| FP | 1 |
| TN | 69 |
| Precision | 0.9907 |
| Recall | 0.9727 |
| Wrong-type alert rate | 0.1909 |
| Preflight coverage | 0.9909 |
| Preflight unavailable rate | 0.0091 |
| Semantic trace coverage | 1.0000 |
| Precision-safe mixed score | 0.5510 |

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
| `semantic_contradiction` | 31 | 4 | 4 | 1 | 0 |
| `dependency_impact` | 2 | 13 | 3 | 1 | 1 |
| `constraint_violation` | 1 | 0 | 18 | 0 | 1 |
| `temporal_invalidation` | 2 | 3 | 0 | 14 | 1 |

_Detection rule: preflight `final_conflict_type` is authoritative when present. Mixed-report exact-type scoring uses the same derived predicted type for confusion, benign FP accounting, and detector-level breakdowns._
