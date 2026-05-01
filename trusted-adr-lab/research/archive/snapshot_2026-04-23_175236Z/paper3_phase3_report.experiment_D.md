# paper3 Experiment D — Trusted ADR Lab (Wave 4)
Generated: 2026-04-21T22:42:24Z

This companion report re-reports the Wave 4 TAL metrics against the 
legacy `experiment_D` identifier used by earlier paper drafts.

| metric | value |
|--------|------:|
| Core-N exact-type recall | **50.0%** |
| Conflict binary recall | 50.0% |
| Benign FP rate | 50.0% |
| `needs_review` precision | 25.0% |
| `needs_review` recall (ambiguous) | 25.0% |
| Unsafe forced-type rate (ambiguous) | 0.0% |
| `dependency_impact` coverage | n/a (domain-absent) |

> `dependency_impact` is **n/a** rather than zero because TAL's plain-text ADR corpus has no cross-document dependency triples.  This is an honest corpus-scope limitation, not a detector failure.

