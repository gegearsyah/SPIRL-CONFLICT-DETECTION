# Wilson 95% CIs + McNemar / two-proportion z-test

Script: `scripts/compute_confidence_intervals.py`
Wave 4 RDL log: `c:/Users/GEYE ARDIANSYAH/Downloads/Innovation Hub/SPIRAL-RESEARCH/Beyond Temporal Contradiction/real-data-lab/research/archive/pre_calibration_v3_2026-04-24_072015Z/real_data_lab_execution_log.jsonl`

## Binary scoring conventions

We report two binary views:

- **Strict** (`binary_precision`, `binary_recall`, `binary_f1_mass`, `benign_fp_rate`): any row whose `outcome_class == "detected"` is a positive prediction, even when governance routed it to `needs_review`.  This is the conservative scoring an adversarial reviewer would apply — the `needs_review` channel is "the system raised an alarm" regardless of whether it committed to a typed label.

- **Abstention-aware** (`*_abstain_aware`, `abstain_on_*`): follows AbstentionBench (arXiv:2506.09038) and El-Yaniv & Wiener (2010).  Rows routed to `needs_review` are withheld from the binary tally and counted separately under `abstain_on_conflict` / `abstain_on_benign`.  The paper's Table 2 point estimates align with the abstention-aware view; the strict view is included so reviewers can audit the cost of treating every governance abstention as a typed fire.

Both views are honest; they answer different questions.

## RDL (Wave 4)

| Metric | k / n | p̂ | 95% Wilson CI |
| --- | ---: | ---: | ---: |
| `binary_precision` | 99 / 112 | 0.8839 | [0.8115, 0.9309] |
| `binary_recall` | 99 / 100 | 0.9900 | [0.9455, 0.9982] |
| `binary_f1_mass` | 198 / 212 | 0.9340 | [0.8922, 0.9603] |
| `benign_specificity` | 57 / 70 | 0.8143 | [0.7077, 0.8881] |
| `benign_fp_rate` | 13 / 70 | 0.1857 | [0.1119, 0.2923] |
| `exact_recall_core4` | 76 / 100 | 0.7600 | [0.6677, 0.8331] |
| `exact_recall_core3` | 63 / 80 | 0.7875 | [0.6858, 0.8629] |
| `exact_recall_temporal_invalidation` | 14 / 20 | 0.7000 | [0.4810, 0.8545] |
| `exact_recall_constraint_violation` | 18 / 20 | 0.9000 | [0.6990, 0.9721] |
| `exact_recall_dependency_impact` | 13 / 20 | 0.6500 | [0.4329, 0.8188] |
| `exact_recall_semantic_contradiction` | 31 / 40 | 0.7750 | [0.6250, 0.8768] |
| `exact_recall_ambiguous_case` | 10 / 10 | 1.0000 | [0.7225, 1.0000] |
| `unsafe_forced_type_ambig` | 0 / 10 | 0.0000 | [0.0000, 0.2775] |
| `needs_review_recall_ambig` | 10 / 10 | 1.0000 | [0.7225, 1.0000] |
| `needs_review_precision` | 10 / 120 | 0.0833 | [0.0459, 0.1466] |
| `abstain_on_benign` | 13 / 180 | 0.0722 | [0.0427, 0.1196] |
| `abstain_on_conflict` | 97 / 180 | 0.5389 | [0.4660, 0.6101] |
| `benign_fp_rate_abstain_aware` | 0 / 57 | 0.0000 | [0.0000, 0.0631] |
| `binary_f1_mass_abstain_aware` | 4 / 5 | 0.8000 | [0.3755, 0.9638] |
| `binary_precision_abstain_aware` | 2 / 2 | 1.0000 | [0.3424, 1.0000] |
| `binary_recall_abstain_aware` | 2 / 3 | 0.6667 | [0.2077, 0.9385] |

## Wave 3 vs Wave 4 McNemar (RDL)

_Paired McNemar unavailable: Wave 3 execution log is truncated.  Falling back to two-proportion z-test on aggregate counts where Wave 3 counts are recoverable._

