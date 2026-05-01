# Mixed workload report - Real Data Lab (conflicts + benign)

Generated: 2026-04-10T23:01:28Z

Project: `32f75297-7059-400e-9ec5-2439a87a866e`

## Conflicts (c-* corpus, `real-data-lab/list_conflict.md`)

| Metric | Value |
|--------|------:|
| Rows (injected, c-*) | 110 |
| Binary detected (any alert) | 102 |
| Binary recall | 0.9273 |
| Exact-type detected | 75 |
| Exact-type recall | 0.6818 |
| Cross-type alerts | 21 |
| Abstained rows | 8 |

## Benign (b-* / sb-* corpus, `real-data-lab/list_benign.md`)

| Metric | Value |
|--------|------:|
| Rows (injected, benign IDs) | 70 |
| False positives | 4 |
| True negatives | 66 |
| FP rate | 0.0571 |

## Benign FP by detector

| Detector | Benign FP |
|----------|----------:|
| `semantic_contradiction` | 4 |

## Pooled binary: alert warranted (conflict = positive, benign = negative)

| Metric | Value |
|--------|------:|
| TP | 102 |
| FN | 8 |
| FP | 4 |
| TN | 66 |
| Precision | 0.9623 |
| Recall | 0.9273 |

## Exact-type confusion matrix

| Expected | semantic | dependency | constraint | temporal | none |
|----------|---------:|-----------:|-----------:|---------:|-----:|
| `semantic_contradiction` | 38 | 0 | 0 | 1 | 1 |
| `dependency_impact` | 3 | 12 | 2 | 2 | 1 |
| `constraint_violation` | 6 | 0 | 11 | 0 | 2 |
| `temporal_invalidation` | 4 | 2 | 0 | 14 | 0 |

_Detection rule: semantic rows only score as semantic when `semantic_verdict=detected`; structural rows only score exact-type when their own expected class is detected in preflight or exact-type async fallback. Benign rows do not treat raw notification creation as truth when preflight verdict fields are present._
