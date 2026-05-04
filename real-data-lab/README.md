# Real Data Lab (RDL)

RDL is the paper's primary 180-row mixed workload: 110 conflict rows plus 70 benign controls. It is the source for the paper's headline RDL metrics.

For the paper claim map, start at [`../PAPER_RESULTS_GUIDE.md`](../PAPER_RESULTS_GUIDE.md).

## Canonical Paper Artifacts

| Artifact | What it supports |
| --- | --- |
| [`research/real_data_lab_mixed_report.md`](research/real_data_lab_mixed_report.md) | 180-row mixed workload counts, binary recall/precision, core-4 exact-type recall, benign FP, ambiguity routing, confusion matrix. |
| [`research/wave4_confidence_intervals_v3b.md`](research/wave4_confidence_intervals_v3b.md) | Wilson confidence intervals and strict vs abstention-aware binary scoring. |
| [`research/wave4_confidence_intervals_v3b.json`](research/wave4_confidence_intervals_v3b.json) | Machine-readable confidence interval output. |
| [`research/governance_outcome_diagnostic.md`](research/governance_outcome_diagnostic.md) | Governance outcome diagnostics for Wave 4.3++b. |
| [`research/wave4_constants_provenance.md`](research/wave4_constants_provenance.md) | Threshold provenance and leakage disclosure. |
| [`research/real_data_lab_execution_log.jsonl`](research/real_data_lab_execution_log.jsonl) | Raw current execution log for paper-facing RDL metrics. |
| [`research/archive/pre_v3b_2026-04-24_193439Z/`](research/archive/pre_v3b_2026-04-24_193439Z/) | Pre-v3b snapshot used for the Wave 4.3++b paired comparison. |

## Data Files

| File | Role |
| --- | --- |
| [`list_conflict.md`](list_conflict.md) | Human-readable conflict row list. |
| [`list_benign.md`](list_benign.md) | Human-readable benign row list. |
| [`research/real_data_lab_checkpoints.jsonl`](research/real_data_lab_checkpoints.jsonl) | Run checkpoints. |
| [`research/real_data_lab_error_analysis.jsonl`](research/real_data_lab_error_analysis.jsonl) | Error analysis rows. |
| [`research/real_data_lab_confusion_matrix.md`](research/real_data_lab_confusion_matrix.md) | Confusion matrix companion. |
| [`research/archive/`](research/archive/) | Historical snapshots; useful for ablations, but not all snapshots are canonical for the paper. |

## How to Read the Metrics

- **Strict binary scoring** treats every alert or review route as an alert.
- **Abstention-aware scoring** excludes `needs_review` rows from binary precision/recall to ask whether committed typed labels are correct.
- **Core-4 exact-type recall** covers semantic, dependency, constraint, and temporal rows only.
- **Ambiguous rows** are tracked separately and are not a fifth conflict class.
- **Cross-type alerts** count off-diagonal typed predictions and exclude `none`.

## Replay

Use [`research/RUNBOOK_R4_RDL_REPLAY.md`](research/RUNBOOK_R4_RDL_REPLAY.md) for the paper-facing replay sequence. The scripts live in [`../scripts/`](../scripts/).
