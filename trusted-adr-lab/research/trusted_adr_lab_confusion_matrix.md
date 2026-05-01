# Trusted ADR Lab — Confusion Matrix
Generated: 2026-04-24T20:17:51Z

Rows = expected class, columns = predicted class; `none` column captures abstentions (typed-conflict silence plus `needs_review` routing).

| expected \ predicted | `semantic_contradiction` | `constraint_violation` | `temporal_invalidation` | `none` |
|---|---|---|---|---|
| `semantic_contradiction` | 3 | 0 | 0 | 1 |
| `constraint_violation` | 2 | 0 | 0 | 0 |
| `temporal_invalidation` | 0 | 1 | 1 | 0 |

