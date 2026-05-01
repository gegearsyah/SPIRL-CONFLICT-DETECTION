# Phase 1 Report — Corpus Verification and Edge Creation
Generated: 2026-03-31T23:57:32Z

**Method:** `scripts/paper3_phase1_mcp_run.py` — all Spirl I/O via MCP Streamable HTTP (`tools/call`).

Project UUIDs: `.spirl/config.json` → `projects` (`paper3_data_pipeline`, `paper3_saas`, `paper3_api_service`).
**Basis export (SKF):** `research/paper3_basis.skf.json` — fact keys, kinds, bodies, edges; use for future runs to verify the same logical corpus (diff SKFs; only `project_id` / `spirl_config_snapshot` should change when re-homing).

## Project 1: paper3_data_pipeline (b7e311b5-db87-4bb1-94b3-a0b51ea4caaa)

### Baseline snapshot
| kind | count |
|------|-------|
| api_endpoint | 22 |
| constraint | 12 |
| decision | 12 |
| deployment | 5 |
| feature | 17 |
| migration | 2 |
| monitoring | 4 |
| stack | 14 |
| test | 7 |
| TOTAL | 95 |

Pre-existing conflicts found: 0
Pre-existing conflicts resolved: 0
Clean baseline after cleanup: yes

### Edges (live graph)
| type | count |
|------|-------|
| communicates_with | 18 |
| depends_on | 9 |
| deployed_with | 5 |
| implements | 5 |
| related_to | 25 |
| tested_by | 7 |
| TOTAL | 69 |

Isolated nodes: 0 — none
Graph connected: yes

### Readiness for Phase 2
- Has decision facts: yes — count: 12
- Has stack facts: yes — count: 14
- Has feature facts: yes — count: 17
- Has constraint facts: yes — count: 12
- Has api_endpoint facts: yes — count: 22
- Has typed edges: yes — count: 69
- Clean conflict baseline: yes
- Ready for Phase 2: YES
- Blockers: none

## Project 2: paper3_saas (cdc4e20b-5c49-4feb-aafb-eca3b5157ae2)

### Baseline snapshot
| kind | count |
|------|-------|
| api_endpoint | 20 |
| constraint | 10 |
| decision | 14 |
| deployment | 4 |
| feature | 18 |
| migration | 2 |
| monitoring | 3 |
| stack | 15 |
| test | 6 |
| TOTAL | 92 |

Pre-existing conflicts found: 0
Pre-existing conflicts resolved: 0
Clean baseline after cleanup: yes

### Edges (live graph)
| type | count |
|------|-------|
| communicates_with | 20 |
| depends_on | 12 |
| deployed_with | 4 |
| implements | 8 |
| related_to | 17 |
| tested_by | 6 |
| TOTAL | 67 |

Isolated nodes: 0 — none
Graph connected: yes

### Readiness for Phase 2
- Has decision facts: yes — count: 14
- Has stack facts: yes — count: 15
- Has feature facts: yes — count: 18
- Has constraint facts: yes — count: 10
- Has api_endpoint facts: yes — count: 20
- Has typed edges: yes — count: 67
- Clean conflict baseline: yes
- Ready for Phase 2: YES
- Blockers: none

## Project 3: paper3_api_service (aa75eda0-4205-44ef-b692-5248ff0eb956)

### Baseline snapshot
| kind | count |
|------|-------|
| api_endpoint | 22 |
| constraint | 12 |
| decision | 12 |
| deployment | 5 |
| feature | 18 |
| migration | 2 |
| monitoring | 4 |
| stack | 14 |
| test | 7 |
| TOTAL | 96 |

Pre-existing conflicts found: 0
Pre-existing conflicts resolved: 0
Clean baseline after cleanup: yes

### Edges (live graph)
| type | count |
|------|-------|
| communicates_with | 22 |
| depends_on | 10 |
| deployed_with | 5 |
| implements | 6 |
| related_to | 20 |
| tested_by | 7 |
| TOTAL | 70 |

Isolated nodes: 0 — none
Graph connected: yes

### Readiness for Phase 2
- Has decision facts: yes — count: 12
- Has stack facts: yes — count: 14
- Has feature facts: yes — count: 18
- Has constraint facts: yes — count: 12
- Has api_endpoint facts: yes — count: 22
- Has typed edges: yes — count: 70
- Clean conflict baseline: yes
- Ready for Phase 2: YES
- Blockers: none

## Cross-project summary
| metric | p1 | p2 | p3 |
|--------|----|----|-----|
| total facts | 95 | 92 | 96 |
| total edges | 69 | 67 | 70 |
| pre-existing conflicts resolved | 0 | 0 | 0 |
| isolated nodes remaining | 0 | 0 | 0 |
| ready for phase 2 | true | true | true |

## Phase 1 overall status
All projects ready for Phase 2: YES
Blockers: none
