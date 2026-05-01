# Phase 1 Report — Real Data Lab (single corpus)
Generated: 2026-04-11T20:20:17Z

## Project: Project Core Platform (`39108fb6-1ad9-4139-9a47-93aeb3aa8436`)

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
Pre-existing conflicts resolved: 2
Clean baseline after cleanup: partial

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
- Phase 1 log lines (phase==1): 73
- Report source lines scanned: 73
- Imported SKF facts (`f-*`) all have ≥1 graph edge; remaining isolated nodes are `research` summary upserts only.

