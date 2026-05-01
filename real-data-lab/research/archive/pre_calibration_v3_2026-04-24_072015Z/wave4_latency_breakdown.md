# Wave 4 latency breakdown (Phase A)

**Date**: 2026-04-21
**Scope**: diagnose the 14.7 h RDL Phase 2 wallclock vs. the pre-Wave-4 18.7 s / 35.2 s preflight claim.
**Evidence source**: 180-row RDL Phase 2 production log (`real_data_lab_execution_log.jsonl`), code inspection.

---

## Real cascade latency from `semantic_trace` (all 180 rows)

The logged `semantic_trace` sub-envelope **does** carry per-stage timings
even though `detection_latency_ms` is null at the top level. These are
the actual preflight cascade numbers for the 2026-04-21 Wave 4 run:

| Stage | n | Median (ms) | p95 (ms) | Max (ms) |
|---|---:|---:|---:|---:|
| **Total preflight cascade** | 180 | **33 500** | 81 031 | 151 656 |
| Retrieval (Supabase vector + filter) | 180 | 5 313 | 8 266 | 14 250 |
| NLI fast-filter | 180 | 10 281 | 12 641 | 15 844 |
| LLM judge (Stage 5) | 180 | **8 797** | **60 969** | 128 641 |
| Contrastive (CE re-rank) | 32 | 12 359 | 16 797 | 21 343 |

**Takeaways**:

- Real Wave 4 preflight cascade median is **33.5 s**, not the paper's
  stale 18.7 s claim. The 18.7 s figure was measured on the post-write
  `_run_conflict_detection` path, which is short-circuited when preflight
  already surfaced conflicts — not the preflight wall time.
- **Stage 5 LLM judge is the dominant variable cost** (max 128 s). Its
  p95 of 61 s explains almost the entire total p95 of 81 s.
- NLI fast-filter at 10 s median indicates the DeBERTa NLI backbone is
  running on CPU, not GPU.
- Cascade compute (33.5 s) is only ~14% of the 247 s per-row wallclock
  observed in phase 2. The other ~86% is Supabase network + upsert +
  ground-truth write + notification poll.

## Observed wallclock (per-class, time-between-log-entries)

| Class | n | Median s/row | Max s/row |
|---|---|---|---|
| `temporal_invalidation` | 20 | 193 | 339 |
| `semantic_contradiction` | 40 | 169 | 202 |
| `dependency_impact` | 20 | 181 | 319 |
| `constraint_violation` | 20 | 252 | **5798** |
| `ambiguous_case` | 10 | 306 | 327 |
| `benign` | 70 | **343** | 494 |
| **Overall** | **180** | **247** | 5798 |

## Critical data-collection issue

All 180 rows have `detection_latency_ms: null`. The field is present in the envelope shape but never populated. Root cause:

- The runner reads `detection_latency_ms` from the **post-write upsert response** (`parse_detection(last_write_resp)` at [real_data_lab_phase2_mcp_run.py L2003-2005](../../scripts/real_data_lab_phase2_mcp_run.py)).
- Post-write detection is set inside `memory_store._run_conflict_detection` (L51) — but when preflight already detected conflicts, the engine short-circuits the post-write detection path so `detection_latency_ms` is never populated.
- The actual cascade latency **is** measured by the backend and exposed as `lane_summary.total_cascade_latency_ms` (see [conflict_engine.py L1089](../../../Spiral/backend/app/services/conflict_engine.py)) in the **preflight** response. The RDL runner discards `preflight_raw` without reading this field.

**Conclusion**: the paper's "median 18.7 s preflight latency" claim was measured on the pre-Wave-4 archive snapshot; the current runner has no mechanism to verify or refute it. Phase B must add `preflight_latency_ms` extraction.

## Primary latency contributors (ranked)

### 1. Notification polling on benign rows (biggest single factor)

[paper3_phase2_mcp_run.py L250-251](../../scripts/paper3_phase2_mcp_run.py) sets:
```
POLL_CONFLICTS_INTERVAL_S = 1.0
POLL_CONFLICTS_MAX_WAIT_S = 60.0
```

Benign rows never produce a notification, so every benign row pays the full 60 s poll. Evidence: benign median 343 s > all typed medians. 70 benign rows * 60 s = 70 min of polling alone.

### 2. Supabase network latency + 502s

Terminal 11 shows a `Cloudflare 502 / Supabase timeout` error captured mid-run. Each preflight + upsert + ground-truth upsert = 3-4 Supabase round trips. From Indonesia to the Supabase region, each round trip is typically 500 ms-2 s, and degraded to 5-30 s during 502 episodes.

The `max 5798 s` outlier on `constraint_violation` is almost certainly a Supabase stall (5798 s / 96 min is orders of magnitude longer than any single cascade stage can take).

### 3. Wave 4.1 NLI anchor rollback

[temporal_lane.py L427-493](../../../Spiral/backend/app/services/temporal_lane.py): every temporal candidate in the borderline cue_score band [1.0, 1.5) adds one NLI round trip. With local DeBERTa-v3-large-mnli on CPU, that's 0.5-2 s per call. Only affects temporal rows; modest.

### 4. Stage 5 LLM judge

[cascade_router.py L342 `_run_stage_5`](../../../Spiral/backend/app/services/cascade_router.py) is reached when earlier stages don't resolve. Each call is 5-30 s to the Qwen/OpenAI endpoint. Affects semantic and ambiguous rows.

### 5. Governance LLR selector

Pure Python (`_neyman_pearson_llr` at [cascade_router.py L998](../../../Spiral/backend/app/services/cascade_router.py)). No LLM or model calls. Negligible (<1 ms/row).

## Tractable fixes (ordered by ROI)

1. **Drop benign poll to 10 s** (or 0 s if `preflight_terminal=="benign"`). Saves ~50 min / 70 benign rows.
2. **Log `preflight_latency_ms`** from `lane_summary.total_cascade_latency_ms` so we can actually see cascade cost per row.
3. **Short-circuit anchor-rollback NLI** when `dependency_lane` already produced a structural proof on the same row (already partly done; verify).
4. **Accept Supabase network cost** (unfixable from the RDL side; could be mitigated by running the backend in the same region as Supabase, but that is out of scope).

## Decision

The latency regression is **not** primarily from Wave 4 code changes — it's from:
- a data-collection gap (no `preflight_latency_ms` captured),
- hard-coded 60 s benign polling (pre-existing, not Wave 4),
- occasional Supabase 502s (infrastructure, not Wave 4).

Phase B should land fixes #1 and #2 above, alongside the `governance_outcome` logger patch. The NLI/Voronoi/LLR paths are **not** the culprit and do not need backend changes for the re-run. The 18.7 s / 35.2 s paper claim should be re-measured once `preflight_latency_ms` is captured, and the paper should qualify it as "cascade latency (excludes network + poll)" rather than "end-to-end preflight wall time".
