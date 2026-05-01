# Semantic validation report (contradiction + benign)

Generated: 2026-04-02T11:12:04Z

Project: `8d95aa5d-31cf-422a-bb4f-ec92a9a427ca`

- **experiment_id:** `hoyer_0p25`
- **Hoyer λ (provenance tag; configure on Spirl):** `0.25`

## Corpus

- **Positives:** `list_conflict_semantic_only.md` (40 × `semantic_contradiction`), phase **4** in this experiment’s log.
- **Negatives:** `list_benign_semantic_focus.md`, phase **5**.

- **This run’s log:** `real-data-lab/research/real_data_lab_semantic_execution_log.hoyer_0p25.jsonl`

## Pooled binary metrics

Positive = semantic contradiction injection (**should alert**). Negative = benign injection (**should not alert**).

| Metric | Count / value |
|--------|---------------:|
| TP (semantic, detected) | 34 |
| FN (semantic, missed) | 6 |
| FP (benign, alerted) | 26 |
| TN (benign, clean) | 0 |
| Precision TP/(TP+FP) | 0.5667 |
| Recall TP/(TP+FN) | 0.8500 |

_Detection rule (injection-level): `inline_detected` OR `async_observed.detected` OR `notification.created`._

## Artifacts

- `real_data_lab_semantic_execution_log.hoyer_0p25.jsonl`
- `real_data_lab_semantic_checkpoints.hoyer_0p25.jsonl`

