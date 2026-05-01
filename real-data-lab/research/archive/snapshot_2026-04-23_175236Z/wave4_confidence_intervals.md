# Wilson 95% CIs + McNemar / two-proportion z-test

Script: `scripts/compute_confidence_intervals.py`
Wave 4 RDL log: `real-data-lab/research/archive/wave4_target_2026-04-21_final/real_data_lab_execution_log.jsonl`
Wave 3 aggregate counts: `real-data-lab/research/wave3_baseline_counts.json`
TAL log: `trusted-adr-lab/research/trusted_adr_lab_execution_log.jsonl`

## Binary scoring conventions

We report two binary views:

- **Strict** (`binary_precision`, `binary_recall`, `binary_f1_mass`, `benign_fp_rate`): any row whose `outcome_class == "detected"` is a positive prediction, even when governance routed it to `needs_review`.  This is the conservative scoring an adversarial reviewer would apply — the `needs_review` channel is "the system raised an alarm" regardless of whether it committed to a typed label.

- **Abstention-aware** (`*_abstain_aware`, `abstain_on_*`): follows AbstentionBench (arXiv:2506.09038) and El-Yaniv & Wiener (2010).  Rows routed to `needs_review` are withheld from the binary tally and counted separately under `abstain_on_conflict` / `abstain_on_benign`.  The paper's Table 2 point estimates align with the abstention-aware view; the strict view is included so reviewers can audit the cost of treating every governance abstention as a typed fire.

Both views are honest; they answer different questions.

## RDL (Wave 4)

| Metric | k / n | p̂ | 95% Wilson CI |
| --- | ---: | ---: | ---: |
| `binary_precision` | 98 / 105 | 0.9333 | [0.8687, 0.9673] |
| `binary_recall` | 98 / 100 | 0.9800 | [0.9300, 0.9945] |
| `binary_f1_mass` | 196 / 205 | 0.9561 | [0.9187, 0.9767] |
| `benign_specificity` | 63 / 70 | 0.9000 | [0.8077, 0.9507] |
| `benign_fp_rate` | 7 / 70 | 0.1000 | [0.0493, 0.1923] |
| `exact_recall_core4` | 77 / 100 | 0.7700 | [0.6785, 0.8416] |
| `exact_recall_core3` | 64 / 80 | 0.8000 | [0.6995, 0.8730] |
| `exact_recall_temporal_invalidation` | 15 / 20 | 0.7500 | [0.5313, 0.8881] |
| `exact_recall_constraint_violation` | 19 / 20 | 0.9500 | [0.7639, 0.9911] |
| `exact_recall_dependency_impact` | 13 / 20 | 0.6500 | [0.4329, 0.8188] |
| `exact_recall_semantic_contradiction` | 30 / 40 | 0.7500 | [0.5981, 0.8581] |
| `exact_recall_ambiguous_case` | 0 / 10 | 0.0000 | [0.0000, 0.2775] |
| `unsafe_forced_type_ambig` | 10 / 10 | 1.0000 | [0.7225, 1.0000] |
| `needs_review_recall_ambig` | 0 / 10 | 0.0000 | [0.0000, 0.2775] |
| `needs_review_precision` | 0 / 5 | 0.0000 | [0.0000, 0.4345] |
| `abstain_on_benign` | 5 / 180 | 0.0278 | [0.0119, 0.0634] |
| `abstain_on_conflict` | 0 / 180 | 0.0000 | [0.0000, 0.0209] |
| `benign_fp_rate_abstain_aware` | 2 / 65 | 0.0308 | [0.0085, 0.1054] |
| `binary_f1_mass_abstain_aware` | 196 / 200 | 0.9800 | [0.9497, 0.9922] |
| `binary_precision_abstain_aware` | 98 / 100 | 0.9800 | [0.9300, 0.9945] |
| `binary_recall_abstain_aware` | 98 / 100 | 0.9800 | [0.9300, 0.9945] |

## TAL (Wave 4)

| Metric | k / n | p̂ | 95% Wilson CI |
| --- | ---: | ---: | ---: |
| `binary_precision` | 6 / 9 | 0.6667 | [0.3542, 0.8794] |
| `binary_recall` | 6 / 8 | 0.7500 | [0.4093, 0.9285] |
| `binary_f1_mass` | 12 / 17 | 0.7059 | [0.4687, 0.8672] |
| `benign_specificity` | 3 / 6 | 0.5000 | [0.1876, 0.8124] |
| `benign_fp_rate` | 3 / 6 | 0.5000 | [0.1876, 0.8124] |
| `exact_recall_core4` | 4 / 8 | 0.5000 | [0.2152, 0.7848] |
| `exact_recall_core3` | 4 / 8 | 0.5000 | [0.2152, 0.7848] |
| `exact_recall_temporal_invalidation` | 2 / 2 | 1.0000 | [0.3424, 1.0000] |
| `exact_recall_constraint_violation` | 0 / 2 | 0.0000 | [0.0000, 0.6576] |
| `exact_recall_semantic_contradiction` | 2 / 4 | 0.5000 | [0.1500, 0.8500] |
| `exact_recall_ambiguous_case` | 1 / 4 | 0.2500 | [0.0456, 0.6994] |
| `unsafe_forced_type_ambig` | 0 / 4 | 0.0000 | [0.0000, 0.4899] |
| `needs_review_recall_ambig` | 1 / 4 | 0.2500 | [0.0456, 0.6994] |
| `needs_review_precision` | 1 / 9 | 0.1111 | [0.0199, 0.4350] |
| `abstain_on_benign` | 3 / 18 | 0.1667 | [0.0584, 0.3922] |
| `abstain_on_conflict` | 5 / 18 | 0.2778 | [0.1250, 0.5087] |
| `benign_fp_rate_abstain_aware` | 0 / 3 | 0.0000 | [0.0000, 0.5615] |
| `binary_f1_mass_abstain_aware` | 2 / 4 | 0.5000 | [0.1500, 0.8500] |
| `binary_precision_abstain_aware` | 1 / 1 | 1.0000 | [0.2065, 1.0000] |
| `binary_recall_abstain_aware` | 1 / 3 | 0.3333 | [0.0615, 0.7923] |

## Wave 3 vs Wave 4 McNemar (RDL)

_Paired McNemar unavailable: Wave 3 execution log is truncated.  Falling back to two-proportion z-test on aggregate counts where Wave 3 counts are recoverable._

## Wave 3 vs Wave 4 two-proportion z-test (unpaired fallback)

_Wave 3 paired execution log is truncated; we fall back to a two-proportion z-test on the aggregate confusion-matrix counts recoverable from the archive.  This test has strictly less statistical power than McNemar on paired data.  When the R4 replay produces a full Wave 3 paired log, rerun this script to replace this table with the exact-binomial McNemar numbers._

| Metric | W3 k/n | W4 k/n | W3 p̂ | W4 p̂ | Δ | two-prop p |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `exact_recall_temporal_invalidation` | 15/20 | 15/20 | 0.7500 | 0.7500 | +0.0000 | 1.0000 |
| `exact_recall_constraint_violation` | 19/20 | 19/20 | 0.9500 | 0.9500 | +0.0000 | 1.0000 |
| `exact_recall_dependency_impact` | 14/20 | 13/20 | 0.7000 | 0.6500 | -0.0500 | 0.7357 |
| `exact_recall_semantic_contradiction` | 28/40 | 30/40 | 0.7000 | 0.7500 | +0.0500 | 0.6165 |

