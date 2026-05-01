# Phase 3 Report - Real Data Lab

Generated: 2026-04-21T21:08:36Z

- `project_id`: `ba546025-9c6f-438a-a661-89500d6bec7a`
- Architecture label: `predicate_routed_staged_embedding_nli`
- Architecture doc: `Spiral/docs/CONFLICT_DETECTION_ARCHITECTURE.md`
- Report status: `publishable`

## Mixed workload summary

| Metric | Value |
|--------|------:|
| Binary recall | 0.9909 |
| Core-4 exact-type recall | 0.7800 |
| All-row exact-type recall | 0.7091 |
| Wrong-type alert rate | 0.1909 |
| Benign FP rate | 0.0286 |
| Benign specificity | 0.9714 |
| Preflight coverage | 0.9818 |
| Preflight unavailable rate | 0.0182 |
| Semantic trace coverage | 1.0000 |
| Precision-safe mixed score | 0.5573 |

## Governance outcome (Wave 4.3) — data-collection gap

Neyman-Pearson LLR selector (arXiv:2505.15008) promotes `governance_outcome` to a first-class preflight field and is scored against the AbstentionBench (arXiv:2506.09038) protocol.

> **Known data gap (2026-04-21)**: The runner version that produced this execution
> log did not extract `governance_outcome` from the preflight envelope, so all
> 180 rows below are logged as `unset`.  The backend itself was producing
> `governance_outcome` correctly — the Trusted ADR Lab (TAL) run on the same
> day with `config_fingerprint=e97787bed902bfd9` captured it on every row
> (18 rows, zero `unset`).  A patched runner landed the same day (see
> `scripts/real_data_lab_phase2_mcp_run.py` — `_governance_outcome_from_result`
> and `_preflight_latency_ms_from_result` helpers).  **The paper's Wave 4.3
> governance_outcome column is therefore sourced from the TAL run**, not
> from this RDL snapshot.

| Metric | Value |
|--------|------:|
| `needs_review` precision | 0.0000 (RDL not captured — see TAL 25.0%) |
| `needs_review` recall on ambiguous rows | 0.0000 (RDL not captured — see TAL 25.0%) |
| Unsafe forced-type rate (ambiguous) | 1.0000 (RDL not captured — see TAL 0.0%) |
| Ambiguous rows routed to `needs_review` (TP) | 0 (RDL not captured) |
| Benign rows routed to `needs_review` (FP) | 0 (RDL not captured) |
| Typed-conflict rows routed to `needs_review` (FN) | 0 (RDL not captured) |
| Governance outcome counts | `{"typed_conflict": 0, "needs_review": 0, "benign": 0, "unset": 180}` |

## Preflight cascade latency (real, from `semantic_trace`)

Extracted from the logged `semantic_trace` sub-envelope across all 180 phase-2 rows.  This is the **actual** Wave 4 preflight cascade wall time; the top-level `detection_latency_ms` is null on every row because post-write sync detection is short-circuited whenever preflight already surfaced conflicts.

| Stage | n | Median (ms) | p95 (ms) | Max (ms) |
|---|---:|---:|---:|---:|
| **Total preflight cascade** | 180 | **33 500** | 81 031 | 151 656 |
| Retrieval (Supabase vector + filter) | 180 | 5 313 | 8 266 | 14 250 |
| NLI fast-filter | 180 | 10 281 | 12 641 | 15 844 |
| LLM judge (Stage 5) | 180 | 8 797 | **60 969** | 128 641 |
| Contrastive (CE re-rank, activated on 32/180) | 32 | 12 359 | 16 797 | 21 343 |

Stage 5 LLM-judge p95 at 61 s drives almost the entire end-to-end p95.  See `wave4_latency_breakdown.md` for the full end-to-end decomposition (cascade compute is ~14% of the 247 s per-row wallclock; the rest is Supabase network + notification polling).

## Benign diagnostics

| Metric | Value |
|--------|------:|
| Semantic benign FP | 0 |
| Constraint benign FP | 1 |
| Dependency benign FP | 1 |
| Semantic budget-exhausted benign count | 1 |

## Coherence / authority summary

| Metric | Value |
|--------|------:|
| Preflight-first detected | 108 |
| Async-only recoveries | 1 |
| Preflight/async disagreements | 14 |
| Winning plane counts | `{"semantic": 49, "structural": 59}` |
| Detector-plane authority | `nested_preflight_authority_when_available` |

## Report integrity

| Field | Value |
|-------|------:|
| Report integrity OK | `True` |
| Integrity notes | `none` |

## Contract audit

| Field | Value |
|-------|------:|
| Rows scored | 180 |
| Contract-complete rows | 180 |
| Contract-incomplete rows | 0 |
| Semantic trace missing | 0 |

## Benign FP by detector

| Detector | FP |
|----------|---:|
| `constraint_violation` | 1 |
| `dependency_impact` | 1 |

## Exact-type confusion matrix

| Expected | semantic | dependency | constraint | temporal | none |
|----------|---------:|-----------:|-----------:|---------:|-----:|
| `semantic_contradiction` | 30 | 4 | 4 | 2 | 0 |
| `dependency_impact` | 2 | 14 | 3 | 1 | 0 |
| `constraint_violation` | 1 | 0 | 19 | 0 | 0 |
| `temporal_invalidation` | 1 | 3 | 0 | 15 | 1 |
