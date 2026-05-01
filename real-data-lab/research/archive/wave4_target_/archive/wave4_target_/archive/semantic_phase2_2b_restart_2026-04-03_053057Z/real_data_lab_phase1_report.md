# Phase 1 Report — Real Data Lab (single corpus)
Generated: 2026-04-03T04:45:50Z

## Project: Project Core Platform (`cfdb4767-226a-4474-8976-c0e2573c7681`)

### Baseline snapshot

| kind | count |
|------|-------|
| api_endpoint | 14 |
| constraint | 10 |
| decision | 10 |
| deployment | 6 |
| feature | 10 |
| migration | 7 |
| monitoring | 7 |
| research | 2 |
| stack | 10 |
| test | 5 |
| **TOTAL** | **81** |

Pre-existing conflicts found: 0
Pre-existing conflicts resolved: 0
Clean baseline after cleanup: yes

### Edge creation
Edges created (logged): 2

### Graph verification
- Node count: 82
- Edge count: 70
- Isolated nodes (all kinds): 1
- Isolated SKF corpus facts (`f-*` keys): 0
- SKF keys covered by edge plan: 79
- Connected (all nodes): False
- SKF subgraph connected (no isolated `f-*`): True
- Edges by type:
  - `depends_on`: 16
  - `implements`: 10
  - `related_to`: 43
  - `replaces`: 1

### Overall status
- Phase 1 log lines (phase==1): 5
- Report source lines scanned: 5
- Imported SKF facts (`f-*`) all have ≥1 graph edge; remaining isolated nodes are `research` summary upserts only.

