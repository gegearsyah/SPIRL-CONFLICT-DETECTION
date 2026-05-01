# Phase 2 Report — Conflict Injection and Detection

> **Paper 3 experiment:** C  
> **Architecture label:** spirl_mcp_stack_v2  

Generated: 2026-04-01T05:37:37Z
Total conflicts injected: 200 (target: 200)
Mean injection time: 55.2s per injection
Transport: Spirl MCP (Streamable HTTP), script `scripts/paper3_phase2_mcp_run.py`

## Injection summary by class

| class | injected | inline_detected_in_upsert | notification_matched_poll |
|-------|----------|----------------------------|---------------------------|
| semantic_contradiction | 50 | 0 | 50 |
| dependency_impact | 50 | 0 | 50 |
| constraint_violation | 50 | 0 | 50 |
| temporal_invalidation | 50 | 0 | 50 |
| TOTAL | 200 | 0 | 200 |

*Inline metrics* come only from the synchronous upsert JSON (`detection` dict). When detection is scheduled in the background, this column is expected to be 0. *Notification matched (poll)* reflects `list_conflicts_v1` polling (up to 60s per injection) and is the correct detection signal for Experiment B+ async pipelines.

## Injection summary by project

| project | injected | detected | missed |
|---------|----------|----------|--------|
| b7e311b5-db87-4bb1-94b3-a0b51ea4caaa | 67 | 67 | 0 |
| cdc4e20b-5c49-4feb-aafb-eca3b5157ae2 | 67 | 67 | 0 |
| aa75eda0-4205-44ef-b692-5248ff0eb956 | 66 | 66 | 0 |

## Baseline simulation

| class | baseline_detectable | baseline_missed |
|-------|--------------------|---------------------|
| semantic_contradiction | 0 | 50 |
| dependency_impact | 0 | 50 |
| constraint_violation | 0 | 50 |
| temporal_invalidation | 50 | 0 |
| TOTAL | 50 | 150 |

## Detection latency

### Inline (from upsert response only)

| metric | value |
|--------|-------|
| Mean inline detection latency | N/A (async detection; inline metrics not returned by upsert) |
| Min inline latency | N/A |
| Max inline latency | N/A |
| Inline latency data points | 0 |

### Observed (notification `created_at` minus upsert completion time)

| metric | value |
|--------|-------|
| Mean observed detection latency | 586ms |
| Min observed latency | 312 |
| Max observed latency | 708 |
| Observed latency data points | 200 |

## Performance

| metric | value |
|--------|-------|
| Mean injection time | 55.2s |
| Min injection time | 43.0s |
| Max injection time | 74.6s |

## Anomalies

none

## Phase 2 status

- All 200 conflicts injected: yes
- Ground truth records written: 200
- Baseline simulation complete: yes
- Ready for Phase 3 scoring: YES
- Blockers: none
