# Mixed workload report - Real Data Lab (conflicts + benign)

Generated: 2026-04-11T13:33:05Z

Project: `63aa1d80-6928-4ed7-82ec-afdc2cc8a2f7`

## Conflicts (c-* corpus, `real-data-lab/list_conflict.md`)

| Metric | Value |
|--------|------:|
| Rows (injected, c-*) | 110 |
| Binary detected (any alert) | 102 |
| Binary recall | 0.9273 |
| Exact-type detected | 76 |
| Exact-type recall | 0.6909 |
| Cross-type alerts | 17 |
| Abstained rows | 8 |

## Benign (b-* / sb-* corpus, `real-data-lab/list_benign.md`)

| Metric | Value |
|--------|------:|
| Rows (injected, benign IDs) | 70 |
| False positives | 9 |
| True negatives | 61 |
| FP rate | 0.1286 |

## Preflight / async coherence

| Metric | Value |
|--------|------:|
| Disagreement rows | 60 |
| Async stronger than preflight | 0 |
| Async-only benign FP | 0 |
| Conflict rows recovered async | 0 |
| Preflight-rejected but async-detected | 56 |

## Detector coherence mix

| Coherence | Rows |
|-----------|-----:|
| `coherent` | 43 |
| `disagreement` | 60 |
| `none` | 69 |
| `preflight_only` | 8 |

## Benign FP by detector

| Detector | Benign FP |
|----------|----------:|
| `semantic_contradiction` | 9 |

## Pooled binary: alert warranted (conflict = positive, benign = negative)

| Metric | Value |
|--------|------:|
| TP | 102 |
| FN | 8 |
| FP | 9 |
| TN | 61 |
| Precision | 0.9189 |
| Recall | 0.9273 |

## Exact-type confusion matrix

| Expected | semantic | dependency | constraint | temporal | none |
|----------|---------:|-----------:|-----------:|---------:|-----:|
| `semantic_contradiction` | 39 | 0 | 0 | 0 | 1 |
| `dependency_impact` | 8 | 10 | 0 | 0 | 2 |
| `constraint_violation` | 1 | 0 | 15 | 0 | 4 |
| `temporal_invalidation` | 8 | 0 | 0 | 12 | 0 |

_Detection rule: semantic rows only score as semantic when `semantic_verdict=detected`; structural rows only score exact-type when their own expected class is detected in preflight or exact-type async fallback. Benign rows do not treat raw notification creation as truth when preflight verdict fields are present._
