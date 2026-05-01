# Trusted ADR Lab — Mixed Workload Report (Wave 4)
Generated: 2026-04-24T09:21:36Z
Project: `7b2e5807-a910-4b18-bd8d-f52f310dd51d`

## Workload
- Typed conflict rows: **16** (semantic=8, constraint=4, temporal=4)
- Ambiguity rows: **8**
- Benign rows: **15**

## Pooled detection
- Binary recall (conflict rows only): **75.0%**
- Core-N exact-type recall (semantic+constraint+temporal, `dependency_impact=n/a`): **50.0%**
- Pooled precision (typed TP / (TP + benign FP)): **75.0%**
- Benign specificity: **73.3%** (FP rate: 26.7%)
- Wrong-type alert rate on typed rows: **25.0%**

## Per-class exact-type recall
| class | injected | binary | exact | cross-type | abstained |
|-------|---------:|-------:|------:|-----------:|----------:|
| `semantic_contradiction` | 8 | 6 | 6 | 0 | 2 |
| `constraint_violation` | 4 | 2 | 0 | 2 | 2 |
| `temporal_invalidation` | 4 | 4 | 2 | 2 | 0 |
| `dependency_impact` | n/a | n/a | n/a | n/a | n/a |

> Footnote — `dependency_impact` is **domain-absent** in TAL: ADRs are self-contained markdown files with no cross-document `depends_on` / `implements` triples.  Marked `n/a` to avoid penalizing the detector for a class the corpus cannot express.

## Governance outcome (Wave 4.3)
- `needs_review` precision (ambig→needs_review / (ambig+benign→needs_review)): **14.3%**
- `needs_review` recall on ambiguous rows: **25.0%**
- Unsafe forced-type rate on ambiguous rows: **0.0%**
- Outcome counts: `typed_conflict`=2, `needs_review`=28, `benign`=9, `unset`=0

## Benign FP detector breakdown
| detector | count |
|----------|------:|
| `semantic_contradiction` | 4 |

## Notes

- Metrics computed by `scripts/trusted_adr_lab_mcp_pipeline.py::compute_tal_metrics`.
- Scoring contract matches RDL: same preflight/async resolver, same `governance_outcome` extraction, same row_contract shape.
- References: Neyman-Pearson selector (arXiv:2505.15008), AbstentionBench protocol (arXiv:2506.09038).
