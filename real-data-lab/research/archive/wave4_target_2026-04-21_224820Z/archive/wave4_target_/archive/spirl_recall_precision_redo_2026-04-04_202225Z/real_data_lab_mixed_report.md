# Mixed workload report — Real Data Lab (conflicts + benign)

Generated: 2026-04-04T18:53:39Z

Project: `02baae60-b271-4a34-9c28-5f85cbaa38cb`

## Conflicts (c-* corpus, `real-data-lab/list_conflict.md`)

| Metric | Value |
|--------|------:|
| Rows (injected, c-*) | 110 |
| Detected (alert) | 47 |
| Recall (TP / (TP+FN)) | 0.4273 |

## Benign (b-* / sb-* corpus, `real-data-lab/list_benign.md`)

| Metric | Value |
|--------|------:|
| Rows (injected, benign IDs) | 40 |
| False positives (alert when gold_should_alert false) | 5 |
| True negatives | 35 |
| FP rate (FP / N_benign) | 0.1250 |

## Pooled binary: alert warranted (conflict = positive, benign = negative)

| Metric | Value |
|--------|------:|
| TP | 47 |
| FN | 63 |
| FP | 5 |
| TN | 35 |
| Precision | 0.9038 |
| Recall | 0.4273 |

_Detection rule (injection-level): same as Phase 3 — `inline_detected` OR `async_observed.detected` OR `notification.created`._
