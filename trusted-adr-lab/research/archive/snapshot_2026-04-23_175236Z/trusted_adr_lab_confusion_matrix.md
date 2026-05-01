# Trusted ADR Lab — Confusion Matrix
Generated: 2026-04-21T22:42:24Z

Rows = expected class, columns = predicted class; `none` column captures abstentions (typed-conflict silence plus `needs_review` routing).

| expected \ predicted | `semantic_contradiction` | `constraint_violation` | `temporal_invalidation` | `none` |
|---|---|---|---|---|
| `semantic_contradiction` | 2 | 0 | 0 | 2 |
| `constraint_violation` | 0 | 0 | 0 | 2 |
| `temporal_invalidation` | 0 | 0 | 2 | 0 |

