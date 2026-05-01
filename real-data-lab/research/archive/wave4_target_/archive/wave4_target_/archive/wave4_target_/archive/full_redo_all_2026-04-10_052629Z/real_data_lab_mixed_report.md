# Mixed workload report - Real Data Lab (conflicts + benign)

Generated: 2026-04-10T03:39:05Z

Project: `70baf95f-a31a-49f2-82dc-689937c105c3`

## Conflicts (c-* corpus, `real-data-lab/list_conflict.md`)

| Metric | Value |
|--------|------:|
| Rows (injected, c-*) | 110 |
| Binary detected (any alert) | 106 |
| Binary recall | 0.9636 |
| Exact-type detected | 83 |
| Exact-type recall | 0.7545 |
| Cross-type alerts | 15 |
| Abstained rows | 4 |

## Benign (b-* / sb-* corpus, `real-data-lab/list_benign.md`)

| Metric | Value |
|--------|------:|
| Rows (injected, benign IDs) | 70 |
| False positives | 21 |
| True negatives | 49 |
| FP rate | 0.3000 |

## Benign FP by detector

| Detector | Benign FP |
|----------|----------:|
| `constraint_violation` | 7 |
| `semantic_contradiction` | 14 |

## Pooled binary: alert warranted (conflict = positive, benign = negative)

| Metric | Value |
|--------|------:|
| TP | 106 |
| FN | 4 |
| FP | 21 |
| TN | 49 |
| Precision | 0.8346 |
| Recall | 0.9636 |

## Exact-type confusion matrix

| Expected | semantic | dependency | constraint | temporal | none |
|----------|---------:|-----------:|-----------:|---------:|-----:|
| `semantic_contradiction` | 37 | 0 | 1 | 1 | 1 |
| `dependency_impact` | 4 | 13 | 2 | 0 | 1 |
| `constraint_violation` | 2 | 0 | 18 | 0 | 0 |
| `temporal_invalidation` | 3 | 2 | 0 | 15 | 0 |

_Detection rule: semantic rows only score as semantic when `semantic_verdict=detected`; structural rows only score exact-type when their own expected class is detected in preflight or exact-type async fallback. Benign rows do not treat raw notification creation as truth when preflight verdict fields are present._
