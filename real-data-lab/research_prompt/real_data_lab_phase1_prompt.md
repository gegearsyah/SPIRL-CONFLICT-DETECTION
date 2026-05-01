# Phase 1 — Real Data Lab: Corpus Verification and Edge Creation
## Multiagent prompt with structured logging (single real corpus project)

**Log schema fields:** Same as Paper 3 — see [`../../research_prompt/paper3_log_schema.md`](../../research_prompt/paper3_log_schema.md).  
**Write logs only under** `real-data-lab/research/` (not `research/paper3_*.jsonl`).

---

## MCP-FIRST RULE (CRITICAL)

You MUST use MCP tools for ALL interactions with Spirl. Do NOT fall back to HTTP REST calls.  
If an MCP call fails, retry via MCP (up to 3 retries with exponential backoff: 1s, 2s, 4s).  
Only if all 3 MCP retries fail should you log the failure and move on — never silently switch to HTTP.

The MCP transport is Streamable HTTP (NOT SSE). Your `.cursor/mcp.json` must NOT include `"type": "sse"`.

---

## SPIRL MCP (exact tool IDs)

| Intent | Tool | Notes |
|--------|------|-------|
| **List all facts** | `list_facts_v1` | Paginate: `limit` ≤ 1000, repeat with `offset` until empty. |
| Hybrid search (optional) | `memory_query_v1` | If used, pass an explicit high `limit`. |
| **List edges** | `list_fact_edges` | `limit` up to 500; page if needed. |
| **Graph summary (optional)** | `get_project_graph_data` | |
| **Create edge** | `create_fact_edge` | `source_fact_key`, `target_fact_key`, `edge_type`, optional `weight` / `metadata`. |
| **List conflicts** | `list_conflicts_v1` | |
| **Resolve conflict** | `resolve_conflict_v1` | `resolution` ∈ `accepted` \| `rejected` \| `merged` \| `deferred`; narrative in **execution log only**. |
| **Upsert research fact** | `memory_upsert_fact_v1` | For baseline / summary facts. |

**Neo4j primary:** If `NEO4J_PRIMARY=true`, trust MCP counts over SQL-only checks.

---

## PATHS (this track)

| Artifact | Path (relative to `Beyond Temporal Contradiction/`) |
|----------|------------------------------------------------------|
| Execution log | `real-data-lab/research/real_data_lab_execution_log.jsonl` |
| Checkpoints | `real-data-lab/research/real_data_lab_checkpoints.jsonl` |
| Phase 1 report | `real-data-lab/research/real_data_lab_phase1_report.md` |

---

## BEFORE YOU START

### 1. Resume check

Read `real-data-lab/research/real_data_lab_checkpoints.jsonl`. Look for entries with `"phase": 1`.

| Checkpoint status | Action |
|-------------------|--------|
| `complete` | Skip execution; regenerate report from logs if asked. |
| `failed` | Resume from `last_successful_action` / `resume_point`. |
| `in_progress` | Continue from last log line. |
| None | Start fresh from Step 1. |

### 2. Prerequisites

- [ ] MCP connection active (`get_pm_context`)
- [ ] Directory exists: `real-data-lab/research/`
- [ ] Writable: `real_data_lab_execution_log.jsonl`, `real_data_lab_checkpoints.jsonl`

On failure, append a checkpoint with `status`: `failed` and stop.

---

## PROJECT CONNECTION

Use **one** Spirl project for the imported real-data-lab SKF.

Read **`../../.spirl/config.json`**:

- Prefer `real_data_lab_project_id`, or  
- `projects.real_data_lab_project_core_platform` (or the key you set via `scripts/import_real_data_lab_skf_mcp.py --write-config`).

Do not hardcode UUIDs in prompts; always use the id from config for this run.

---

## STEP 1 — Baseline snapshot (READ + WRITE)

#### 1a. Phase start checkpoint

Append to `real-data-lab/research/real_data_lab_checkpoints.jsonl`:

```json
{
  "timestamp": "{ISO_NOW}",
  "phase": 1,
  "checkpoint_type": "phase_start",
  "agent_id": "rdl_phase1_corpus_builder",
  "status": "in_progress",
  "prerequisites_checked": true,
  "notes": "Real Data Lab Phase 1 — corpus verification"
}
```

#### 1b. Context and facts

Call `get_pm_context` for the project.  
Call **`list_facts_v1`** with `limit=1000` and increasing `offset` until a page returns fewer than `limit` facts.

**Immediately** append `baseline_snapshot` to `real-data-lab/research/real_data_lab_execution_log.jsonl` (same JSON shape as in [`../../research_prompt/paper3_phase1_prompt.md`](../../research_prompt/paper3_phase1_prompt.md) § Step 1b).

#### 1c. Pre-existing conflicts

Call **`list_conflicts_v1`**. For each conflict, **`resolve_conflict_v1`** (typically `accepted` for baseline cleanup). Log each as `conflict_resolved` to `real_data_lab_execution_log.jsonl`.

#### 1d. Baseline research fact

Upsert a fact, for example:

- `key`: `research.rdl.baseline.{short_project_slug}`
- `kind`: `research`
- `body`: summary of totals and resolved pre-existing conflicts

---

## STEP 2 — Edge creation (READ + WRITE)

Same logic as Paper 3 Phase 1 Step 2: paginate facts, create **`create_fact_edge`** links with **only** valid Spirl `edge_type` values (**not** `validates`; use `related_to` where needed).  
**Maximum 5 edges per fact.** Log each `edge_created` line to **`real-data-lab/research/real_data_lab_execution_log.jsonl`**.

After all edges, upsert a summary fact, e.g. `research.rdl.edges.justification.{short_project_slug}`.

---

## STEP 3 — Graph verification (READ + WRITE)

Use **`list_facts_v1`** + **`list_fact_edges`** (paginated). Log `graph_verified` to `real_data_lab_execution_log.jsonl`.

Append `project_complete` checkpoint to **`real-data-lab/research/real_data_lab_checkpoints.jsonl`** (same shape as Paper 3 `checkpoint_type: project_complete`, one project only).

---

## STEP 4 — Report generation (READ)

Run **after** Steps 1–3 are complete for this project.

1. Read `real-data-lab/research/real_data_lab_execution_log.jsonl` (filter `phase === 1`).
2. Write **`real-data-lab/research/real_data_lab_phase1_report.md`** using the single-project sections from the template in [`../../research_prompt/paper3_phase1_prompt.md`](../../research_prompt/paper3_phase1_prompt.md) § Step 4c (omit Project 2 / 3 and cross-project table; keep one project block + short overall status).

3. Append phase complete checkpoint to `real_data_lab_checkpoints.jsonl`:

```json
{
  "timestamp": "{ISO_NOW}",
  "phase": 1,
  "checkpoint_type": "phase_complete",
  "agent_id": "rdl_phase1_corpus_builder",
  "status": "complete",
  "report_generated": true,
  "report_path": "real-data-lab/research/real_data_lab_phase1_report.md",
  "log_entries_written": {count},
  "next_phase_prerequisites_met": true|false,
  "notes": "Real Data Lab Phase 1 complete for single corpus project"
}
```

---

## HARD RULES

1. **Log immediately** after each action.
2. **Do not inject conflicts** (that is a separate phase if you add one).
3. **Do not change existing fact bodies** except adding edges and explicit research summary facts as above.
4. **Resume** from `real_data_lab_checkpoints.jsonl` + tail of `real_data_lab_execution_log.jsonl`.

---

## SUCCESS CRITERIA

- [ ] Baseline snapshot logged  
- [ ] Pre-existing conflicts resolved and logged  
- [ ] Every fact has ≥1 edge or is marked intentionally isolated  
- [ ] Edges logged with justifications  
- [ ] Graph verified and logged  
- [ ] `real_data_lab_phase1_report.md` written  
- [ ] Phase complete checkpoint written  

---

## IF EXECUTION FAILS

Write a `phase_failed` checkpoint (same pattern as [`../../research_prompt/paper3_phase1_prompt.md`](../../research_prompt/paper3_phase1_prompt.md) § IF EXECUTION FAILS) to **`real-data-lab/research/real_data_lab_checkpoints.jsonl`**.
