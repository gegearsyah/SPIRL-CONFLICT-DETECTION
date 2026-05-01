# Wilson 95% CIs + McNemar / two-proportion z-test

Script: `scripts/compute_confidence_intervals.py`
Wave 4 RDL log: `real-data-lab/research/real_data_lab_execution_log.jsonl`

## Binary scoring conventions

We report two binary views:

- **Strict** (`binary_precision`, `binary_recall`, `binary_f1_mass`, `benign_fp_rate`): any row whose `outcome_class == "detected"` is a positive prediction, even when governance routed it to `needs_review`.  This is the conservative scoring an adversarial reviewer would apply — the `needs_review` channel is "the system raised an alarm" regardless of whether it committed to a typed label.

- **Abstention-aware** (`*_abstain_aware`, `abstain_on_*`): follows AbstentionBench (arXiv:2506.09038) and El-Yaniv & Wiener (2010).  Rows routed to `needs_review` are withheld from the binary tally and counted separately under `abstain_on_conflict` / `abstain_on_benign`.  The paper's Table 2 point estimates align with the abstention-aware view; the strict view is included so reviewers can audit the cost of treating every governance abstention as a typed fire.

Both views are honest; they answer different questions.

## RDL (Wave 4)

| Metric | k / n | p̂ | 95% Wilson CI |
| --- | ---: | ---: | ---: |
| `binary_precision` | 98 / 100 | 0.9800 | [0.9300, 0.9945] |
| `binary_recall` | 98 / 100 | 0.9800 | [0.9300, 0.9945] |
| `binary_f1_mass` | 196 / 200 | 0.9800 | [0.9497, 0.9922] |
| `benign_specificity` | 68 / 70 | 0.9714 | [0.9017, 0.9921] |
| `benign_fp_rate` | 2 / 70 | 0.0286 | [0.0079, 0.0983] |
| `exact_recall_core4` | 73 / 100 | 0.7300 | [0.6357, 0.8073] |
| `exact_recall_core3` | 60 / 80 | 0.7500 | [0.6452, 0.8319] |
| `exact_recall_temporal_invalidation` | 13 / 20 | 0.6500 | [0.4329, 0.8188] |
| `exact_recall_constraint_violation` | 18 / 20 | 0.9000 | [0.6990, 0.9721] |
| `exact_recall_dependency_impact` | 13 / 20 | 0.6500 | [0.4329, 0.8188] |
| `exact_recall_semantic_contradiction` | 29 / 40 | 0.7250 | [0.5717, 0.8389] |
| `exact_recall_ambiguous_case` | 8 / 10 | 0.8000 | [0.4902, 0.9433] |
| `unsafe_forced_type_ambig` | 2 / 10 | 0.2000 | [0.0567, 0.5098] |
| `needs_review_recall_ambig` | 8 / 10 | 0.8000 | [0.4902, 0.9433] |
| `needs_review_precision` | 8 / 80 | 0.1000 | [0.0515, 0.1851] |
| `abstain_on_benign` | 2 / 180 | 0.0111 | [0.0031, 0.0396] |
| `abstain_on_conflict` | 70 / 180 | 0.3889 | [0.3207, 0.4617] |
| `benign_fp_rate_abstain_aware` | 0 / 68 | 0.0000 | [0.0000, 0.0535] |
| `binary_f1_mass_abstain_aware` | 56 / 58 | 0.9655 | [0.8827, 0.9905] |
| `binary_precision_abstain_aware` | 28 / 28 | 1.0000 | [0.8794, 1.0000] |
| `binary_recall_abstain_aware` | 28 / 30 | 0.9333 | [0.7868, 0.9815] |

## Wave 3 vs Wave 4 McNemar (RDL)

_Paired McNemar unavailable: Wave 3 execution log is truncated.  Falling back to two-proportion z-test on aggregate counts where Wave 3 counts are recoverable._

