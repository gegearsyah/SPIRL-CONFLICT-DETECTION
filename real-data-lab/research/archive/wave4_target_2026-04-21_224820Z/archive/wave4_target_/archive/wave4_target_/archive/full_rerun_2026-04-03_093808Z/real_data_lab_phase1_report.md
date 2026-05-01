# Phase 1 Report — Real Data Lab (single corpus)
Generated: 2026-04-03T09:16:55Z

## Project: Project Core Platform (`3c96f3ff-ee7c-4347-b8ae-2a1b12fb0776`)

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
| stack | 10 |
| test | 5 |
| **TOTAL** | **79** |

Pre-existing conflicts found: 0
Pre-existing conflicts resolved: 0
Clean baseline after cleanup: yes

### Edge creation
Edges created (logged): 69

### Graph verification
- Node count: 81
- Edge count: 69
- Isolated nodes (all kinds): 2
- Isolated SKF corpus facts (`f-*` keys): 0
- SKF keys covered by edge plan: 79
- Connected (all nodes): False
- SKF subgraph connected (no isolated `f-*`): True
- Edges by type:
  - `depends_on`: 16
  - `implements`: 10
  - `related_to`: 43

### Overall status
- Phase 1 log lines (phase==1): 71
- Report source lines scanned: 71
- Imported SKF facts (`f-*`) all have ≥1 graph edge; remaining isolated nodes are `research` summary upserts only.

