# Phase 3 Report — Real Data Lab

Generated: 2026-04-04T22:23:15Z

## Project

- `project_id`: `b2dea5c0-d504-4514-9560-df505a6b9198`
- Architecture label: `predicate_routed_staged_embedding_nli`
- Architecture doc (reference): `Spiral/docs/CONFLICT_DETECTION_ARCHITECTURE.md`

## Single corpus — cross-project table N/A

Overall F1 (pooled binary, from execution log): **0.8462** (precision 0.7333, recall 1.0000).

Semantic rows use preflight-primary scoring when `semantic_primary_detected` is present; async notification remains a transport/matcher metric.

## Detection by expected conflict_class (c-* rows)

| conflict_class | injected | alerted | recall |
|----------------|----------|---------|--------|
| `semantic_contradiction` | 40 | 40 | 1.0000 |
| `dependency_impact` | 20 | 20 | 1.0000 |
| `constraint_violation` | 20 | 20 | 1.0000 |
| `temporal_invalidation` | 20 | 20 | 1.0000 |
| `ambiguous_case` | 10 | 10 | 1.0000 |

## Mixed workload (from log)

| Metric | Value |
|--------|------:|
| Conflict rows (c-*) | 110 |
| Conflict alerted | 110 |
| Conflict recall | 1.0000 |
| Benign rows | 40 |
| Benign FP | 40 |
| Benign FP rate | 1.0000 |
| Pooled precision | 0.7333 |
| Pooled recall | 1.0000 |

## RQ facts

Upserted (if `--upsert-rq`): `research.rdl.results.rq1` … `rq3`.

## Limitations

One imported real graph plus scripted injections; not three independent synthetic domains.

