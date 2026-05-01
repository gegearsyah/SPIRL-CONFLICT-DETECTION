# Mixed workload report - Real Data Lab (conflicts + benign)

Generated: 2026-04-06T18:20:48Z

Project: `0134d78e-4ac2-4cb4-8b7c-2c7693c79266`

## Conflicts (c-* corpus, `real-data-lab/list_conflict.md`)

| Metric | Value |
|--------|------:|
| Rows (injected, c-*) | 110 |
| Binary detected (any alert) | 63 |
| Binary recall | 0.5727 |
| Exact-type detected | 30 |
| Exact-type recall | 0.2727 |
| Cross-type alerts | 29 |
| Abstained rows | 47 |

## Benign (b-* / sb-* corpus, `real-data-lab/list_benign.md`)

| Metric | Value |
|--------|------:|
| Rows (injected, benign IDs) | 40 |
| False positives | 11 |
| True negatives | 29 |
| FP rate | 0.2750 |

## Benign FP by detector

| Detector | Benign FP |
|----------|----------:|
| `semantic_contradiction` | 11 |

## Pooled binary: alert warranted (conflict = positive, benign = negative)

| Metric | Value |
|--------|------:|
| TP | 63 |
| FN | 47 |
| FP | 11 |
| TN | 29 |
| Precision | 0.8514 |
| Recall | 0.5727 |

## Exact-type confusion matrix

| Expected | semantic | dependency | constraint | temporal | none |
|----------|---------:|-----------:|-----------:|---------:|-----:|
| `semantic_contradiction` | 25 | 0 | 0 | 0 | 15 |
| `dependency_impact` | 8 | 0 | 0 | 0 | 12 |
| `constraint_violation` | 5 | 0 | 1 | 0 | 10 |
| `temporal_invalidation` | 10 | 0 | 0 | 4 | 4 |

_Detection rule: semantic rows only score as semantic when `semantic_verdict=detected`; structural rows only score exact-type when their own expected class is detected in preflight or exact-type async fallback. Benign rows do not treat raw notification creation as truth when preflight verdict fields are present._
