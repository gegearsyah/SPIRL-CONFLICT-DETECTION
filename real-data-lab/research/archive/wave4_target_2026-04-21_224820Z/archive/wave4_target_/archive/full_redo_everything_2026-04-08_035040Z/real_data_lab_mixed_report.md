# Mixed workload report - Real Data Lab (conflicts + benign)

Generated: 2026-04-07T21:22:28Z

Project: `e4b4cd05-1edf-4f38-b531-b3464af8b851`

## Conflicts (c-* corpus, `real-data-lab/list_conflict.md`)

| Metric | Value |
|--------|------:|
| Rows (injected, c-*) | 110 |
| Binary detected (any alert) | 59 |
| Binary recall | 0.5364 |
| Exact-type detected | 30 |
| Exact-type recall | 0.2727 |
| Cross-type alerts | 27 |
| Abstained rows | 51 |

## Benign (b-* / sb-* corpus, `real-data-lab/list_benign.md`)

| Metric | Value |
|--------|------:|
| Rows (injected, benign IDs) | 70 |
| False positives | 14 |
| True negatives | 56 |
| FP rate | 0.2000 |

## Benign FP by detector

| Detector | Benign FP |
|----------|----------:|
| `semantic_contradiction` | 14 |

## Pooled binary: alert warranted (conflict = positive, benign = negative)

| Metric | Value |
|--------|------:|
| TP | 59 |
| FN | 51 |
| FP | 14 |
| TN | 56 |
| Precision | 0.8082 |
| Recall | 0.5364 |

## Exact-type confusion matrix

| Expected | semantic | dependency | constraint | temporal | none |
|----------|---------:|-----------:|-----------:|---------:|-----:|
| `semantic_contradiction` | 23 | 0 | 0 | 1 | 16 |
| `dependency_impact` | 8 | 1 | 0 | 0 | 11 |
| `constraint_violation` | 9 | 0 | 2 | 0 | 9 |
| `temporal_invalidation` | 9 | 0 | 0 | 4 | 7 |

_Detection rule: semantic rows only score as semantic when `semantic_verdict=detected`; structural rows only score exact-type when their own expected class is detected in preflight or exact-type async fallback. Benign rows do not treat raw notification creation as truth when preflight verdict fields are present._
