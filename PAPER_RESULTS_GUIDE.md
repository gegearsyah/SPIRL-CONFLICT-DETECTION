# Paper Results Guide

This file is the reader map for the EMNLP paper artifacts in this release. Use it to connect each paper claim to the exact report, raw log, and corpus file that supports it.

The release contains the evaluation and offline-lab slice of Spirl. The full production backend lives outside this bundle. For paper replication, the important question is usually not "which folder has the most files?" but "which artifact is canonical for this claim?"

> **Review-submission note:** before submitting this bundle as supplementary material for double-blind review, place it in an anonymized archive or repository and remove any project paths, organization names, credentials, or deployment URLs that could identify the authors.

## How to Read the Governance Metrics

The paper treats Spirl as a write-time governance system for shared product memory, not only as a binary contradiction detector.

| Metric family | Governance reading |
| --- | --- |
| Binary precision/recall/F1 | Did the system raise any alert or review route? Useful but incomplete for product-memory writes. |
| Exact-type recall | Remediation-route accuracy: did the alert point to the right repair path? |
| Cross-type alerts | Wrong repair-path events, such as sending a timeline repair to semantic adjudication. These can be hidden by binary scoring. |
| Unsafe forced-type rate | Ambiguous writes that were forced into a typed repair instead of being deferred. |
| `needs_review` precision/recall | Explicit deferral when the system should not commit to a typed route. This prevents silent wrong typing but adds review load. |

## Canonical Artifacts

| Topic | Canonical artifact | Raw data / log | Notes |
| --- | --- | --- | --- |
| RDL mixed workload headline metrics | [`real-data-lab/research/real_data_lab_mixed_report.md`](real-data-lab/research/real_data_lab_mixed_report.md) | [`real-data-lab/research/real_data_lab_execution_log.jsonl`](real-data-lab/research/real_data_lab_execution_log.jsonl) | Source for 180-row RDL mixed workload: binary recall/precision, exact-type recall, benign FP, ambiguity routing, confusion matrix. |
| RDL Wilson CIs and abstention-aware scoring | [`real-data-lab/research/wave4_confidence_intervals_v3b.md`](real-data-lab/research/wave4_confidence_intervals_v3b.md) | [`real-data-lab/research/wave4_confidence_intervals_v3b.json`](real-data-lab/research/wave4_confidence_intervals_v3b.json) | Source for confidence intervals in the paper's main result table. |
| RDL Wave 4.3++b governance diagnostics | [`real-data-lab/research/governance_outcome_diagnostic.md`](real-data-lab/research/governance_outcome_diagnostic.md) | [`real-data-lab/research/governance_outcome_diagnostic.json`](real-data-lab/research/governance_outcome_diagnostic.json) | Explains why rows routed to `typed_conflict`, `needs_review`, or `benign`. |
| RDL pre-v3b vs post-v3b comparison | [`real-data-lab/research/archive/pre_v3b_2026-04-24_193439Z/`](real-data-lab/research/archive/pre_v3b_2026-04-24_193439Z/) and current `research/` log | Current and archived `real_data_lab_execution_log.jsonl` files | Supports the paired benign-alert reduction discussed in the paper. |
| RDL constants and leakage disclosure | [`real-data-lab/research/wave4_constants_provenance.md`](real-data-lab/research/wave4_constants_provenance.md) | Backend constants are referenced by path in that audit | Use this for threshold provenance, the 14-row ambiguity calibration overlap, and constraint co-location guard disclosure. |
| TAL paper-facing row audit | [`trusted-adr-lab/research/trusted_adr_lab_execution_log.jsonl`](trusted-adr-lab/research/trusted_adr_lab_execution_log.jsonl) plus [`trusted-adr-lab/research/trusted_adr/trusted_*_rows.jsonl`](trusted-adr-lab/research/trusted_adr/) | [`trusted-adr-lab/research/trusted_adr_lab_execution_log.jsonl`](trusted-adr-lab/research/trusted_adr_lab_execution_log.jsonl) | The paper's TAL claims are summarized in the main paper text and grounded in the raw TAL log/row materialization: 18 rows, 8 typed, 4 ambiguous, 6 benign. |
| TAL generated reports | [`trusted-adr-lab/research/trusted_adr_lab_mixed_report.md`](trusted-adr-lab/research/trusted_adr_lab_mixed_report.md) | [`trusted-adr-lab/research/trusted_adr_lab_execution_log.jsonl`](trusted-adr-lab/research/trusted_adr_lab_execution_log.jsonl) | Useful pipeline output, but the main paper text and raw execution log are canonical when generated summaries use different aggregation conventions. |
| Semantic-first proxy / offline cascade ablation | [`architecture/OFFLINE_CASCADE_ABLATION.md`](architecture/OFFLINE_CASCADE_ABLATION.md) | [`state-orchestration-lab/results/ablation_sweep_summary.json`](state-orchestration-lab/results/ablation_sweep_summary.json), [`state-orchestration-lab/`](state-orchestration-lab/README.md) outputs | Appendix-style evidence for the RDL semantic slice: 40 semantic-conflict rows plus 26 semantic-focused benign controls. It is not a Semantic Commit reproduction and not the live LLM-primary evaluation. |

## Paper Claim Ledger

| Paper claim | Where to verify | Important caveat |
| --- | --- | --- |
| RDL has 180 rows: 110 conflict rows and 70 benign controls. | [`real-data-lab/research/real_data_lab_mixed_report.md`](real-data-lab/research/real_data_lab_mixed_report.md), [`real-data-lab/list_conflict.md`](real-data-lab/list_conflict.md), [`real-data-lab/list_benign.md`](real-data-lab/list_benign.md) | The 110 conflict rows include 10 ambiguous rows; core-4 exact-type recall excludes ambiguity. |
| RDL strict binary precision/recall/F1 are about 0.98. | [`real-data-lab/research/wave4_confidence_intervals_v3b.md`](real-data-lab/research/wave4_confidence_intervals_v3b.md) | Strict scoring treats any `detected` row as an alert, even if governance routes it to `needs_review`. |
| RDL core-4 exact-type recall is 0.73. | [`real-data-lab/research/real_data_lab_mixed_report.md`](real-data-lab/research/real_data_lab_mixed_report.md) and [`wave4_confidence_intervals_v3b.md`](real-data-lab/research/wave4_confidence_intervals_v3b.md) | This is typed-class recall over semantic, dependency, constraint, and temporal rows. |
| RDL has 24 cross-type typed alerts. | [`real-data-lab/research/real_data_lab_mixed_report.md`](real-data-lab/research/real_data_lab_mixed_report.md) | `none` outcomes are not counted as cross-type typed alerts. |
| RDL ambiguous routing improves under Wave 4.3++b: 8/10 ambiguous rows route to `needs_review`, unsafe forced-type is 2/10. | [`real-data-lab/research/real_data_lab_mixed_report.md`](real-data-lab/research/real_data_lab_mixed_report.md), [`wave4_confidence_intervals_v3b.md`](real-data-lab/research/wave4_confidence_intervals_v3b.md) | The governance thresholds were calibrated on a 14-row ambiguity slice that overlaps evaluation rows; see provenance audit. |
| RDL benign FP rate drops to 2/70 strict, 0/68 abstention-aware. | [`real-data-lab/research/wave4_confidence_intervals_v3b.md`](real-data-lab/research/wave4_confidence_intervals_v3b.md) | The abstention-aware view asks whether committed typed labels are correct; it does not mean there was zero review load. |
| TAL binary F1 is lower than RDL and exposes portability/retrieval issues. | Main paper TAL paragraph and [`trusted-adr-lab/research/trusted_adr_lab_execution_log.jsonl`](trusted-adr-lab/research/trusted_adr_lab_execution_log.jsonl) | TAL is a small, out-of-distribution ADR probe. It has no dependency substrate, so `dependency_impact` is `n/a`. |
| TAL strict benign FP is 3/6 but abstention prevents typed commits on those rows. | Main paper TAL paragraph; raw TAL log in [`trusted-adr-lab/research/trusted_adr_lab_execution_log.jsonl`](trusted-adr-lab/research/trusted_adr_lab_execution_log.jsonl) | Generated TAL summary reports may use a different aggregation convention; prefer the main paper claim plus raw log for paper-facing claims. |
| TAL ambiguous unsafe forced-type is 0/4, but only 1/4 ambiguous rows route to `needs_review`. | Main paper TAL paragraph and raw TAL log | Three ambiguous TAL rows under-route to `benign`; this is a real retrieval/threshold limitation. |
| Wave 4 threshold leakage is disclosed. | [`real-data-lab/research/wave4_constants_provenance.md`](real-data-lab/research/wave4_constants_provenance.md) | `governance_llr_threshold=0.35` and `governance_ambiguous_floor=0.15` were calibrated on 10 RDL + 4 TAL ambiguous rows. |
| The semantic-first proxy shows the binary write-conflict tradeoff. | [`state-orchestration-lab/results/ablation_sweep_summary.json`](state-orchestration-lab/results/ablation_sweep_summary.json), appendix semantic ablation table | This is an internal proxy motivated by the same limitation as binary write-conflict systems: high-recall semantic alerting overfires on benign controls, while precision-safe gating misses many contradictions. It should not be cited as a direct Semantic Commit reproduction. |
| The release is not the full Spirl backend. | [`README.md`](README.md), [`architecture/README.md`](architecture/README.md) | This repo ships evaluation artifacts, scripts, and an offline lab. The production MCP/FastAPI backend is separate. |

## Data Inventory

### Real Data Lab (RDL)

| File | Use |
| --- | --- |
| [`real-data-lab/list_conflict.md`](real-data-lab/list_conflict.md) | Human-readable conflict row list. |
| [`real-data-lab/list_benign.md`](real-data-lab/list_benign.md) | Human-readable benign row list. |
| [`real-data-lab/research/real_data_lab_execution_log.jsonl`](real-data-lab/research/real_data_lab_execution_log.jsonl) | Raw current execution log for paper-facing RDL metrics. |
| [`real-data-lab/research/real_data_lab_checkpoints.jsonl`](real-data-lab/research/real_data_lab_checkpoints.jsonl) | Run checkpoints. |
| [`real-data-lab/research/real_data_lab_error_analysis.jsonl`](real-data-lab/research/real_data_lab_error_analysis.jsonl) | Per-row error analysis. |
| [`real-data-lab/research/real_data_lab_confusion_matrix.md`](real-data-lab/research/real_data_lab_confusion_matrix.md) | Confusion matrix companion. |
| [`real-data-lab/research/archive/`](real-data-lab/research/archive/) | Historical snapshots for Wave comparisons and reruns. |

### Trusted ADR Lab (TAL)

| File | Use |
| --- | --- |
| [`trusted-adr-lab/research/trusted_adr/trusted_*_rows.jsonl`](trusted-adr-lab/research/trusted_adr/) | Source row materialization for TAL. |
| [`trusted-adr-lab/research/trusted_adr_lab_execution_log.jsonl`](trusted-adr-lab/research/trusted_adr_lab_execution_log.jsonl) | Raw TAL execution log. |
| [`trusted-adr-lab/research/trusted_adr_lab_confusion_matrix.md`](trusted-adr-lab/research/trusted_adr_lab_confusion_matrix.md) | Generated confusion matrix. |
| [`trusted-adr-lab/research/trusted_adr_lab_mixed_report.md`](trusted-adr-lab/research/trusted_adr_lab_mixed_report.md) | Generated mixed report; useful, but the paper's TAL table should be checked against the qualitative row audit when numbers differ. |
| [`trusted-adr-lab/research/archive/`](trusted-adr-lab/research/archive/) | Historical TAL snapshots. |

## Reading Order

1. Start with [`README.md`](README.md) for the repository layout.
2. Read this guide to identify the canonical paper artifacts.
3. For RDL headline metrics, open [`real_data_lab_mixed_report.md`](real-data-lab/research/real_data_lab_mixed_report.md) and [`wave4_confidence_intervals_v3b.md`](real-data-lab/research/wave4_confidence_intervals_v3b.md).
4. For TAL, read the main paper TAL paragraph alongside [`trusted_adr_lab_execution_log.jsonl`](trusted-adr-lab/research/trusted_adr_lab_execution_log.jsonl) and the materialized row files under [`trusted_adr/`](trusted-adr-lab/research/trusted_adr/).
5. For architecture and offline ablation, read [`architecture/README.md`](architecture/README.md) and [`architecture/OFFLINE_CASCADE_ABLATION.md`](architecture/OFFLINE_CASCADE_ABLATION.md).
6. For replay instructions, use [`real-data-lab/research/RUNBOOK_R4_RDL_REPLAY.md`](real-data-lab/research/RUNBOOK_R4_RDL_REPLAY.md) and [`trusted-adr-lab/README.md`](trusted-adr-lab/README.md).
