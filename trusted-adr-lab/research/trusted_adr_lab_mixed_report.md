# Trusted ADR Lab — Mixed Workload Report (Wave 4)
Generated: 2026-04-24T20:17:51Z
Project: `7b2e5807-a910-4b18-bd8d-f52f310dd51d`

> **Reader note:** this is a generated pipeline report. For the paper-facing TAL numbers, use the main paper TAL paragraph and the artifact map in [`../../PAPER_RESULTS_GUIDE.md`](../../PAPER_RESULTS_GUIDE.md) together with the raw execution log [`trusted_adr_lab_execution_log.jsonl`](trusted_adr_lab_execution_log.jsonl). If this generated summary disagrees with the main paper text and raw log, treat the main paper text/raw log pair as canonical for the paper table.

## Workload
- Typed conflict rows: **8** (semantic=4, constraint=2, temporal=2)
- Ambiguity rows: **4**
- Benign rows: **6**

## Pooled detection
- Binary recall (conflict rows only): **87.5%**
- Core-N exact-type recall (semantic+constraint+temporal, `dependency_impact=n/a`): **50.0%**
- Pooled precision (typed TP / (TP + benign FP)): **87.5%**
- Benign specificity: **83.3%** (FP rate: 16.7%)
- Wrong-type alert rate on typed rows: **37.5%**

## Per-class exact-type recall
| class | injected | binary | exact | cross-type | abstained |
|-------|---------:|-------:|------:|-----------:|----------:|
| `semantic_contradiction` | 4 | 3 | 3 | 0 | 1 |
| `constraint_violation` | 2 | 2 | 0 | 2 | 0 |
| `temporal_invalidation` | 2 | 2 | 1 | 1 | 0 |
| `dependency_impact` | n/a | n/a | n/a | n/a | n/a |

> Footnote — `dependency_impact` is **domain-absent** in TAL: ADRs are self-contained markdown files with no cross-document `depends_on` / `implements` triples.  Marked `n/a` to avoid penalizing the detector for a class the corpus cannot express.

## Governance outcome (Wave 4.3)
- `needs_review` precision (ambig→needs_review / (ambig+benign→needs_review)): **0.0%**
- `needs_review` recall on ambiguous rows: **0.0%**
- Unsafe forced-type rate on ambiguous rows: **0.0%**
- Outcome counts: `typed_conflict`=1, `needs_review`=7, `benign`=10, `unset`=0

## Benign FP detector breakdown
| detector | count |
|----------|------:|
| `semantic_contradiction` | 1 |

## Notes

- Metrics computed by `scripts/trusted_adr_lab_mcp_pipeline.py::compute_tal_metrics`.
- Scoring contract matches RDL: same preflight/async resolver, same `governance_outcome` extraction, same row_contract shape.
- References: Neyman-Pearson selector (arXiv:2505.15008), AbstentionBench protocol (arXiv:2506.09038).
