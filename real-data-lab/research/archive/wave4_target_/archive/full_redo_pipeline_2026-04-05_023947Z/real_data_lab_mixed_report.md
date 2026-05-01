# Mixed workload report — Real Data Lab (conflicts + benign)

Generated: 2026-04-04T22:23:15Z

Project: `b2dea5c0-d504-4514-9560-df505a6b9198`

## Conflicts (c-* corpus, `real-data-lab/list_conflict.md`)

| Metric | Value |
|--------|------:|
| Rows (injected, c-*) | 110 |
| Detected (alert) | 110 |
| Recall (TP / (TP+FN)) | 1.0000 |

## Benign (b-* / sb-* corpus, `real-data-lab/list_benign.md`)

| Metric | Value |
|--------|------:|
| Rows (injected, benign IDs) | 40 |
| False positives (alert when gold_should_alert false) | 40 |
| True negatives | 0 |
| FP rate (FP / N_benign) | 1.0000 |

## Pooled binary: alert warranted (conflict = positive, benign = negative)

| Metric | Value |
|--------|------:|
| TP | 110 |
| FN | 0 |
| FP | 40 |
| TN | 0 |
| Precision | 0.7333 |
| Recall | 1.0000 |

_Detection rule (injection-level): same as Phase 3 — `inline_detected` OR `async_observed.detected` OR `notification.created`._
