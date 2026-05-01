# Phase 1 Report — Corpus Verification and Edge Creation

**Generated:** 2026-03-31T04:05:00Z  
**Evidence:** Live `get_pm_context`, `list_fact_edges`, and `list_conflicts_v1` via Spirl MCP; `research/paper3_execution_log.jsonl` append-only entries for this pass.

**Canonical project IDs** (from `research_prompt/paper3_phase1_prompt.md` and `.spirl/config.json`):

| # | Theme | Project ID |
|---|--------|------------|
| P1 | Data pipeline (paper3_data_pipeline) | `24e91a29-a6db-4b8b-8fd1-7cc0c39eeaa3` |
| P2 | SaaS analytics (paper3_saas) | `f557ed99-1389-4ad5-b5be-5cc42fb94f7a` |
| P3 | Core API service (paper3_api_service) | `17110ac4-017c-4a86-bc45-f643d5da18d6` |

---

## Resume and log hygiene (handoff rules)

- `paper3_checkpoints.jsonl` already contained **phase 1** `phase_complete` (migrated). Per the Phase 1 prompt, a completed phase is not re-executed from Step 1; this run is a **reverification** with fresh MCP reads and an updated report.
- Historical Phase 1 rows in `paper3_execution_log.jsonl` were **backfilled baselines only** (no per-edge `edge_created` lines). Later phases appended normally. This report calls out **live** counts and API behavior so Phase 3/4 agents do not confuse backfill with instrumented edge logging.

---

## Tooling notes (Spirl as deployed here)

- **`list_fact_edges` (MCP)** returned **`total: 0`** for all three projects on 2026-03-31. **`get_pm_context`** still shows a short **“Dependencies (N edges)”** rollup in markdown (13–15 edges). Treat that as **PM-level summary**, not as proof that the edges API is populated — there is an **observability / storage mismatch** to resolve in Spirl if you rely on `list_fact_edges` for metrics.
- **`memory_query_v1`** intermittently failed with MCP transport errors (`Connection closed`); this pass did not depend on it for totals.
- HTTP `GET /v1/memory/{id}/facts` and `POST …/facts/query` returned **empty** fact lists in quick probes while `pm-context` remained rich — prefer **`get_pm_context`** for headline corpus verification until the HTTP path is aligned.
- **`kind: research`** upserts may be rejected by policy (see prior lab notes in git history); Phase 1 metadata keys like `research.p3.*` have historically been stored as **`decision`** with a textual prefix where needed. This reverification did not upsert new facts.

---

## Project 1: Research — Data Pipeline Platform

**ID:** `24e91a29-a6db-4b8b-8fd1-7cc0c39eeaa3`

### Baseline snapshot

| kind | count |
|------|-------|
| decision | 10 |
| stack | 14 |
| feature | 17 |
| constraint | 12 |
| api_endpoint | 22 |
| test | 7 |
| deployment | 5 |
| migration | 2 |
| monitoring | 4 |
| **TOTAL** | **93** |

| Metric | Value |
|--------|--------|
| Pre-existing conflicts found | 0 (`list_conflicts_v1`, unresolved) |
| Pre-existing conflicts resolved | 0 |
| Clean baseline after cleanup | **yes** |

### Edges (API vs PM text)

| Source | depends_on | implements | related_to | other types | total |
|--------|------------|------------|------------|-------------|-------|
| `list_fact_edges` | 0 | 0 | 0 | — | **0** |
| PM “Dependencies” rollup | 5 | 3 | 2 | communicates_with 1, derived_from 1, tested_by 1 | **13** |

| Check | Result |
|--------|--------|
| Isolated nodes | **Not computed** — edge API empty; PM rollup covers a small subgraph only |
| Graph connected | **Unknown** at API layer |

### Readiness for Phase 2 (criteria from Phase 1 prompt)

| Criterion | Result |
|-----------|--------|
| Has decision facts | **yes** — 10 |
| Has stack facts | **yes** — 14 |
| Has feature facts | **yes** — 17 |
| Has constraint facts | **yes** — 12 |
| Has api_endpoint facts | **yes** — 22 |
| Has typed edges | **ambiguous** — PM rollup shows typed deps; **edges API empty** |
| Clean conflict baseline | **yes** (no unresolved rows returned) |
| **Ready for Phase 2** | **YES** for corpus richness; **caveat** on edge API |
| Blockers | **none** for continuing the study; **investigate** `list_fact_edges` vs PM graph |

---

## Project 2: Research — SaaS Analytics Platform

**ID:** `f557ed99-1389-4ad5-b5be-5cc42fb94f7a`

### Baseline snapshot

| kind | count |
|------|-------|
| decision | 12 |
| stack | 15 |
| feature | 18 |
| constraint | 10 |
| api_endpoint | 20 |
| test | 6 |
| deployment | 4 |
| migration | 2 |
| monitoring | 3 |
| **TOTAL** | **90** |

| Metric | Value |
|--------|--------|
| Pre-existing conflicts found | 0 |
| Pre-existing conflicts resolved | 0 |
| Clean baseline after cleanup | **yes** |

### Edges (API vs PM text)

| Source | depends_on | implements | related_to | other | total |
|--------|------------|------------|------------|-------|-------|
| `list_fact_edges` | 0 | 0 | 0 | — | **0** |
| PM “Dependencies” rollup | 9 | 2 | 1 | communicates_with 1, derived_from 1, tested_by 1 | **15** |

### Readiness for Phase 2

| Criterion | Result |
|-----------|--------|
| Has decision / stack / feature / constraint / api_endpoint facts | **yes** (counts above) |
| Has typed edges | **ambiguous** (same API vs PM issue) |
| Clean conflict baseline | **yes** |
| **Ready for Phase 2** | **YES** with same edge-API caveat |
| Blockers | Duplicate-key data hygiene (`constraint.scope_integrations`) was flagged in an **older** report against different UUIDs; re-validate in Spirl UI if analysis depends on uniqueness |

---

## Project 3: Research — Core API Service

**ID:** `17110ac4-017c-4a86-bc45-f643d5da18d6`

### Baseline snapshot

| kind | count |
|------|-------|
| decision | 10 |
| stack | 14 |
| feature | 18 |
| constraint | 12 |
| api_endpoint | 22 |
| test | 7 |
| deployment | 5 |
| migration | 2 |
| monitoring | 4 |
| **TOTAL** | **94** |

| Metric | Value |
|--------|--------|
| Pre-existing conflicts found | 0 |
| Pre-existing conflicts resolved | 0 |
| Clean baseline after cleanup | **yes** |

### Edges (API vs PM text)

| Source | depends_on | implements | related_to | other | total |
|--------|------------|------------|------------|-------|-------|
| `list_fact_edges` | 0 | 0 | 0 | — | **0** |
| PM “Dependencies” rollup | 6 | 2 | 1 | deployed_with 1, communicates_with 1, derived_from 1, tested_by 1 | **13** |

### Readiness for Phase 2

| Criterion | Result |
|-----------|--------|
| Has decision / stack / feature / constraint / api_endpoint facts | **yes** |
| Has typed edges | **ambiguous** |
| Clean conflict baseline | **yes** |
| **Ready for Phase 2** | **YES** with edge-API caveat |
| Blockers | **none** |

---

## Cross-project summary

| metric | p1 | p2 | p3 |
|--------|----|----|-----|
| total facts (PM headline) | 93 | 90 | 94 |
| `list_fact_edges` total | 0 | 0 | 0 |
| PM dependency rollup total | 13 | 15 | 13 |
| unresolved `list_conflicts_v1` | 0 | 0 | 0 |
| ready for phase 2 (corpus) | YES | YES | YES |

---

## Phase 1 overall status

**All projects ready for Phase 2 (corpus present): YES**

**Blockers:** none for narrative Phase 2 **if** you accept PM context as source of truth for corpus size. **Engineering follow-up:** reconcile `list_fact_edges` / HTTP fact listing with `get_pm_context` so Phase 3 metrics can be traced to a single API surface.

---

## Phase status (agent → human, handoff protocol)

| Item | Value |
|------|--------|
| All tasks for this reverification pass complete | **YES** |
| Quality gate (≥80% edge coverage via API) | **NOT MET** at the `list_fact_edges` layer — **UNKNOWN** against full graph |
| Blockers | Edge API empty vs PM rollup |
| Ready for next phase | Phase 2 checkpoint already recorded; Phase 3 should validate metric sources |
| Human review needed | **YES** if you require edge counts from `list_fact_edges` |
