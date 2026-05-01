# Mixed workload report - Real Data Lab (conflicts + benign)

Generated: 2026-04-08T20:32:54Z

Project: `7ce9249b-0fe3-49de-867f-29732c34fd0b`

## Conflicts (c-* corpus, `real-data-lab/list_conflict.md`)

| Metric | Value |
|--------|------:|
| Rows (injected, c-*) | 110 |
| Binary detected (any alert) | 51 |
| Binary recall | 0.4636 |
| Exact-type detected | 29 |
| Exact-type recall | 0.2636 |
| Cross-type alerts | 19 |
| Abstained rows | 59 |

## Benign (b-* / sb-* corpus, `real-data-lab/list_benign.md`)

| Metric | Value |
|--------|------:|
| Rows (injected, benign IDs) | 70 |
| False positives | 23 |
| True negatives | 47 |
| FP rate | 0.3286 |

## Benign FP by detector

| Detector | Benign FP |
|----------|----------:|
| `constraint_violation` | 6 |
| `semantic_contradiction` | 17 |

## Pooled binary: alert warranted (conflict = positive, benign = negative)

| Metric | Value |
|--------|------:|
| TP | 51 |
| FN | 59 |
| FP | 23 |
| TN | 47 |
| Precision | 0.6892 |
| Recall | 0.4636 |

## Exact-type confusion matrix

| Expected | semantic | dependency | constraint | temporal | none |
|----------|---------:|-----------:|-----------:|---------:|-----:|
| `semantic_contradiction` | 9 | 0 | 2 | 1 | 28 |
| `dependency_impact` | 4 | 0 | 1 | 1 | 14 |
| `constraint_violation` | 5 | 0 | 9 | 0 | 6 |
| `temporal_invalidation` | 5 | 0 | 0 | 11 | 4 |

_Detection rule: semantic rows only score as semantic when `semantic_verdict=detected`; structural rows only score exact-type when their own expected class is detected in preflight or exact-type async fallback. Benign rows do not treat raw notification creation as truth when preflight verdict fields are present._
