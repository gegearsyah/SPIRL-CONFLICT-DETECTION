# Mixed workload report — Real Data Lab (conflicts + benign)

Generated: 2026-04-02T20:04:57Z

Project: `5edf987e-1382-4a6d-830e-823544a13f52`

## Conflicts (110 rows, `list_conflict.md`)

| Metric | Value |
|--------|------:|
| Rows (injected, c-*) | 110 |
| Detected (alert) | 72 |
| Recall (TP / (TP+FN)) | 0.6545 |

## Benign (40 rows, `list_benign.md`)

| Metric | Value |
|--------|------:|
| Rows (injected, b-*) | 40 |
| False positives (alert when gold_should_alert false) | 39 |
| True negatives | 1 |
| FP rate (FP / N_benign) | 0.9750 |

## Pooled binary: alert warranted (conflict = positive, benign = negative)

| Metric | Value |
|--------|------:|
| TP | 72 |
| FN | 38 |
| FP | 39 |
| TN | 1 |
| Precision | 0.6486 |
| Recall | 0.6545 |

_Detection rule (injection-level): same as Phase 3 — `inline_detected` OR `async_observed.detected` OR `notification.created`._
