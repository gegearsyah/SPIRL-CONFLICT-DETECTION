# Phase 2 Report — Conflict Injection and Detection

> **Paper 3 experiment:** A  
> **Architecture label:** spirl_mcp_stack_v1  

Generated: 2026-03-31T13:28:59Z
Total conflicts injected: 200 (target: 200)
Mean injection time: 55.8s per injection
Transport: Spirl MCP (Streamable HTTP), script `scripts/paper3_phase2_mcp_run.py`

## Injection summary by class

| class | injected | spirl_preflight_detected | spirl_notification_created |
|-------|----------|--------------------------|---------------------------|
| semantic_contradiction | 50 | 0 | 1 |
| dependency_impact | 50 | 8 | 8 |
| constraint_violation | 50 | 2 | 3 |
| temporal_invalidation | 50 | 4 | 6 |
| TOTAL | 200 | 14 | 18 |

## Injection summary by project

| project | injected | detected | missed |
|---------|----------|----------|--------|
| 24e91a29-a6db-4b8b-8fd1-7cc0c39eeaa3 | 67 | 4 | 63 |
| f557ed99-1389-4ad5-b5be-5cc42fb94f7a | 67 | 7 | 60 |
| 17110ac4-017c-4a86-bc45-f643d5da18d6 | 66 | 7 | 59 |

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
| Mean preflight latency | 3866ms |
| Mean notification latency | 3866ms |
| Min latency | 2531ms |
| Max latency | 5687ms |
| Latency data points | 26 |

## Performance

| metric | value |
|--------|-------|
| Mean injection time | 55.8s |
| Min injection time | 42.0s |
| Max injection time | 78.7s |

## Anomalies

none

## Phase 2 status

- All 200 conflicts injected: yes
- Ground truth records written: 200
- Baseline simulation complete: yes
- Ready for Phase 3 scoring: YES
- Blockers: none
