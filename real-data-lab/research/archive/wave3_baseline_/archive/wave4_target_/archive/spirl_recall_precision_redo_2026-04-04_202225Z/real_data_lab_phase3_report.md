# Phase 3 Report — Real Data Lab

Generated: 2026-04-04T18:53:39Z

## Project

- `project_id`: `02baae60-b271-4a34-9c28-5f85cbaa38cb`
- Architecture label: `predicate_routed_staged_embedding_nli`
- Architecture doc (reference): `Spiral/docs/CONFLICT_DETECTION_ARCHITECTURE.md`

## Single corpus — cross-project table N/A

Overall F1 (pooled binary, from execution log): **0.5802** (precision 0.9038, recall 0.4273).

Semantic rows use preflight-primary scoring when `semantic_primary_detected` is present; async notification remains a transport/matcher metric.

## Detection by expected conflict_class (c-* rows)

| conflict_class | injected | alerted | recall |
|----------------|----------|---------|--------|
| `semantic_contradiction` | 40 | 23 | 0.5750 |
| `dependency_impact` | 20 | 8 | 0.4000 |
| `constraint_violation` | 20 | 3 | 0.1500 |
| `temporal_invalidation` | 20 | 10 | 0.5000 |
| `ambiguous_case` | 10 | 3 | 0.3000 |

## Mixed workload (from log)

| Metric | Value |
|--------|------:|
| Conflict rows (c-*) | 110 |
| Conflict alerted | 47 |
| Conflict recall | 0.4273 |
| Benign rows | 40 |
| Benign FP | 5 |
| Benign FP rate | 0.1250 |
| Pooled precision | 0.9038 |
| Pooled recall | 0.4273 |

## RQ facts

Upserted (if `--upsert-rq`): `research.rdl.results.rq1` … `rq3`.

## Limitations

One imported real graph plus scripted injections; not three independent synthetic domains.

