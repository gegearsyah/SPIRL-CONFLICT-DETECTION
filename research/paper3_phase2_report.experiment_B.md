# Phase 2 Report — Conflict Injection and Detection

> **Paper 3 experiment:** B  
> **Architecture label:** spirl_mcp_stack_v2  

Generated: 2026-03-31T22:47:51Z
Total conflicts injected: 200 (target: 200)
Mean injection time: 46.6s per injection
Transport: Spirl MCP (Streamable HTTP), script `scripts/paper3_phase2_mcp_run.py`

## Injection summary by class

| class | injected | spirl_preflight_detected | spirl_notification_created |
|-------|----------|--------------------------|---------------------------|
| semantic_contradiction | 50 | 0 | 0 |
| dependency_impact | 50 | 0 | 50 |
| constraint_violation | 50 | 0 | 50 |
| temporal_invalidation | 50 | 0 | 50 |
| TOTAL | 200 | 0 | 150 |

## Injection summary by project

| project | injected | detected | missed |
|---------|----------|----------|--------|
| 52af2994-b03e-4236-8aea-700918461af7 | 67 | 51 | 16 |
| ec637c5a-0062-4772-b3b2-8c7727a21c99 | 67 | 50 | 17 |
| 4a847165-a8e7-4d7b-9cb2-54126a284f6c | 66 | 49 | 17 |

## Baseline simulation

| class | baseline_detectable | baseline_missed |
|-------|--------------------|---------------------|
| semantic_contradiction | 0 | 50 |
| dependency_impact | 0 | 50 |
| constraint_violation | 0 | 50 |
| temporal_invalidation | 50 | 0 |
| TOTAL | 50 | 150 |

## Detection latency (where detected)

| metric | value |
|--------|-------|
| Mean preflight latency | 0ms |
| Mean notification latency | 0ms |
| Min latency | 0ms |
| Max latency | 0ms |
| Latency data points | 0 |

## Performance

| metric | value |
|--------|-------|
| Mean injection time | 46.6s |
| Min injection time | 38.2s |
| Max injection time | 60.3s |

## Anomalies

none

## Phase 2 status

- All 200 conflicts injected: yes
- Ground truth records written: 200
- Baseline simulation complete: yes
- Ready for Phase 3 scoring: YES
- Blockers: none
