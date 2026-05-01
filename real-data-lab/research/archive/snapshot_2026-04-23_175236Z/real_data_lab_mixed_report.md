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
| Unsafe forced-type rate | 1.0000 (RDL runner did not capture `governance_outcome`; see TAL 0.0%) |

_Ambiguous rows are tracked separately and excluded from the core-4 headline exact-type metric._  The Wave 4.3 `governance_outcome` column on this run is a data-collection gap — the RDL runner version that produced this report predates the governance_outcome logger patch (landed 2026-04-21).  The TAL Wave 4 run using the consolidated `trusted_adr_lab_mcp_pipeline._inject_row` captured governance_outcome on all 18 rows (`unsafe_forced_type_rate_ambiguous = 0.0`) and is the source of the paper's Wave 4.3 headline.

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

## Scoring contract parity with Trusted ADR Lab (TAL)

| Field | RDL (this report) | TAL Wave 4 |
|---|---|---|
| `config_fingerprint` | `e97787bed902bfd9` | `e97787bed902bfd9` |
| `detector_bundle_version` | `semantic_current+dependency_v3+constraint_v2+temporal_v3+w4_governance_v1` | `semantic_current+dependency_v3+constraint_v2+temporal_v3+w4_governance_v1` |
| `evaluation_contract_version` | `rdl-eval-2026-04-05-v1` | `rdl-eval-2026-04-05-v1` |
| Scoring rule | preflight `final_conflict_type` authoritative when present | identical |
| `governance_outcome` capture | missing (runner gap) | present on all 18/18 rows |

Identical backend config and identical scoring rule across the two corpora validates cross-corpus comparability for the paper's dual-corpus Table 2.
