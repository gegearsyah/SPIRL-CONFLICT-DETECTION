# Phase 2 — Real Data Lab: Conflict injection and detection
## Table-driven corpus from `list_conflict.md` (**one** Spirl project)

**Full log field shapes:** [`../../research_prompt/paper3_log_schema.md`](../../research_prompt/paper3_log_schema.md)  
**Synthetic fallback (Paper 3 style):** only if **`real_data_lab_phase2_mode`** in **`../../.spirl/config.json`** is **`"synthetic"`** — then follow [`../../research_prompt/paper3_phase2_prompt.md`](../../research_prompt/paper3_phase2_prompt.md) but write logs to **`real-data-lab/research/`** and ground truth prefix **`research.rdl.groundtruth.*`**, with **`N`** from **`real_data_lab_injection_target`** (default 200). **Default mode is table-driven (`list_conflict.md`).**

---

## PATHS (this track)

| Artifact | Path (relative to `Beyond Temporal Contradiction/`) |
|----------|------------------------------------------------------|
| **Conflict specification (source)** | `real-data-lab/list_conflict.md` |
| Execution log | `real-data-lab/research/real_data_lab_execution_log.jsonl` |
| Checkpoints | `real-data-lab/research/real_data_lab_checkpoints.jsonl` |
| Phase 2 report | `real-data-lab/research/real_data_lab_phase2_report.md` |

---

## CORPUS: `list_conflict.md`

The markdown table in **`real-data-lab/list_conflict.md`** is the **authoritative injection schedule**. Each **data row** (ID like `c-sem-01`, …) is **one** injection.

**Counts (regenerate if you edit the table):**

| Expected label (table) | `conflict_class` (log / ground truth) | Rows |
|------------------------|----------------------------------------|------|
| `semanticcontradiction` | `semantic_contradiction` | 40 |
| `dependencyimpact` | `dependency_impact` | 20 |
| `constraintviolation` | `constraint_violation` | 20 |
| `temporalinvalidation` | `temporal_invalidation` | 20 |
| `ambiguous` | `ambiguous_case` | 10 |
| **Total** | | **110** |

**Injection target `N`:** By default **`N = 110`** (all rows). Optional smoke test: set **`real_data_lab_injection_limit`** in **`../../.spirl/config.json`** to a positive integer — process only the **first `N` data rows** in file order (after the header row), still logging `corpus_row_id` for each.

**Optional path override:** `real_data_lab_conflict_list_path` — repo-relative path from **`Beyond Temporal Contradiction/`** if you maintain a fork of the table elsewhere.

---

## MCP-FIRST RULE (CRITICAL)

Same as Paper 3 Phase 2: **MCP only**, Streamable HTTP (not SSE), retry up to 3 times.  
Use **`response.detection`** from `memory_upsert_fact_v1` when present (`detection_latency_ms`, `conflicts_detected`, …).  
**No `time.sleep()` inside the upsert request** — do not block the HTTP call waiting for detection.  
**Ground truth upserts:** `skip_embedding: true`, `skip_conflict_check: true`.

### Scheduled async detection (Spirl API)

`memory_upsert_fact_v1` typically returns **`detection.mode: "scheduled"`** (embedding + conflict detection run in a **BackgroundTasks** worker after the response). Inline `conflicts_detected` in the same response is **not** available for that path (`inline_available: false` in logs is expected).

**After each scored upsert**, observe async notifications as follows:

1. **Non-semantic rows:** keep the current full poll budget on cold runs. Poll every **2–5s**.
2. **Semantic rows:** call `memory_check_conflicts_v1(... include_semantic_trace=true, expected_anchor_keys=based_on_facts)` **before** the scored upsert.
3. **Semantic fast-exit policy:** terminal semantic preflight miss → **skip async polling**; semantic preflight hit → **short 15s poll** to capture transport latency; missing/errored semantic preflight → **full fallback poll budget**.
4. **Key matching:** match the notification against either the **new proposed fact key** or any **based_on_facts** key for the row.
5. **`list_conflicts_v1` matching:** filter by **`project_id`** and recency. If the backend uses **Neo4j-primary** mode, `conflict_notifications.fact_id` may be **null**; match using **`details.graph_fact_id`** (or **`details.key`**) equal to the new fact’s UUID / key from the upsert response — do not require `fact_id == upserted_uuid` only.

---

## PROJECT

One project id from **`../../.spirl/config.json`**: `real_data_lab_project_id` or `projects.real_data_lab_project_core_platform` (or the key set by `import_real_data_lab_skf_mcp.py --write-config`).

---

## BEFORE YOU START

### Resume

Read `real-data-lab/research/real_data_lab_checkpoints.jsonl` for `"phase": 2`. If `in_progress`, resume from last `corpus_row_id` / `injection_number` recorded in the checkpoint or in the tail of **`real_data_lab_execution_log.jsonl`**.

### Prerequisites

- [ ] Phase 1 complete for this project (`phase_complete` for phase 1 in **`real_data_lab_checkpoints.jsonl`**)
- [ ] Baseline facts from the SKF import exist so **“Based On Fact”** keys (e.g. `f-api-01`, `f-dec-05`) are present when the table references them — use **`list_facts_v1`** to confirm; if a key is missing, log **`injection_failed`** with `error: baseline_fact_missing` and continue (do not block the whole run unless the operator asked for strict mode)
- [ ] MCP active
- [ ] **`real-data-lab/list_conflict.md`** readable

---

## PARSING EACH TABLE ROW

For each row, read columns:

1. **`corpus_row_id`** — ID column (e.g. `c-sem-01`, `c-dep-20`). Stable identifier for logs and ground truth.
2. **Based On Fact** — Comma-separated baseline fact keys (e.g. `f-api-01`, `f-dep-01, f-feat-03`). Use for traceability in ground truth; optional preflight `list_facts_v1` / `get_pm_context`.
3. **Proposed Fact Details** — Parse from the cell:
   - **`Key:`** → upsert **`key`** (e.g. `p-api-01`, `p-dec-05`)
   - **`Cat:`** → map to Spirl **`kind`** (see table below)
   - **`Val:`** → fact **`body`** / value string (strip surrounding quotes if present)
   - **`Valid:`** → `valid_from` and `valid_until` (e.g. `2026-04-02T10:44Z null` → `valid_from` ISO 8601, `valid_until` null)
4. **Expected Labels** → normalize to **`conflict_class`** (see corpus table above).
5. **Rationale & Realism** — copy into ground truth JSON for human-readable **why**.
6. **Source Support** — optional numeric reference; store in ground truth.

### Category → `kind` (match imported SKF conventions)

| Table `Cat:` | Use `kind` |
|--------------|------------|
| apiendpoint | `api_endpoint` |
| decision | `decision` |
| feature | `feature` |
| stack | `stack` |
| constraint | `constraint` |
| migration | `migration` |
| deployment | `deployment` |
| monitoring | `monitoring` |
| test | `test` |

If the table uses another label, align with **`Project Core Platform.skf.json`** / `list_facts_v1` on existing facts.

---

## GROUND TRUTH KEYS

Use **one fact per row**:

`research.rdl.groundtruth.{corpus_key}`

where **`corpus_key`** = `corpus_row_id` with **hyphens replaced by underscores** (e.g. `c-sem-01` → `c_sem_01`) so the key is a single Spirl-safe token.

Ground truth **`body`** (JSON string or structured object per your Spirl convention) should include at minimum:

- `corpus_row_id`, `conflict_class`, `based_on_facts[]`, `proposed_key`, `proposed_kind`, `rationale_summary`, `expected_label` (raw table text), `source_support` (if any)

Use **`skip_embedding: true`**, **`skip_conflict_check: true`** on this upsert.

---

## STEP 1 — Phase start checkpoint

Append to **`real-data-lab/research/real_data_lab_checkpoints.jsonl`** (same shape as Paper 3 phase 2 start), with:

- `"agent_id": "rdl_phase2_seed_agent"`
- `"notes"` mentioning **`list_conflict.md`** and **`N`** rows to process

---

## STEP 2 — Log injection target

Append **`conflict_injection_start`** to **`real_data_lab_execution_log.jsonl`**:

```json
{
  "timestamp": "{ISO_NOW}",
  "phase": 2,
  "agent_id": "rdl_phase2_seed_agent",
  "action": "conflict_injection_start",
  "project": "{project_id}",
  "result": {
    "source": "real-data-lab/list_conflict.md",
    "mode": "table_driven",
    "target_total": {N},
    "target_per_class": {
      "semantic_contradiction": 40,
      "dependency_impact": 20,
      "constraint_violation": 20,
      "temporal_invalidation": 20,
      "ambiguous_case": 10
    },
    "target_per_project": { "{project_id}": {N} },
    "injection_limit_applied": {true_if_config_limit_else_false}
  }
}
```

If you applied **`real_data_lab_injection_limit`**, set `target_total` to the limited count and note in `result` that class counts are **partial** (only rows processed).

---

## STEP 3 — Injection loop (one row at a time)

**Order:** top-to-bottom data rows in **`list_conflict.md`** (same order as the file).

For **`injection_number`** = 1 … **`N`** (within limit):

1. **Preflight (optional but recommended):** For each baseline key in “Based On Fact”, confirm existence or log warning.
2. **`memory_upsert_fact_v1`** for the **proposed** fact: `key`, `kind`, body/value, and temporal fields from the row. Use the **project** from config. Do **not** set `skip_conflict_check` on this upsert — you want the detector to run.
3. **Poll `list_conflicts_v1`** according to the semantic fast-exit policy above: terminal semantic preflight miss ? skip, semantic preflight hit ? short 15s poll, otherwise use the full budget. Attach `notification_id`, `conflict_type`, and `observed_detection_latency_ms` to the log; set `async_observed.detected` accordingly.
4. **Immediately** append **`conflict_injected`** or **`injection_failed`** to **`real_data_lab_execution_log.jsonl`**, same base shape as Paper 3, with these **additional / overridden** fields:
   - `injection_number` — 1-based index in this run
   - `conflict_class` — normalized class (including **`ambiguous_case`**)
   - `corpus_row_id` — e.g. `c-sem-01`
   - `based_on_facts` — array of baseline keys
   - `proposed_fact_key` — parsed Key from table
   - `ground_truth_key` — `research.rdl.groundtruth.{corpus_key}`
5. Upsert **ground truth** fact `research.rdl.groundtruth.{corpus_key}` with `skip_embedding: true`, `skip_conflict_check: true` (after logging the injection outcome).

**Do not resolve** user-facing conflict notifications — Phase 3 scores them.

---

## STEP 4 — Progress checkpoints

After every **20** successful row attempts (or at end), append **`injection_progress`** to **`real_data_lab_checkpoints.jsonl`**, including:

- `injection_number`, `last_corpus_row_id`
- `class_counts` observed so far (five buckets)
- `"target": {N}`

---

## STEP 5 — Baseline simulation (temporal-only rule)

After all **`N`** rows:

1. Apply the **same temporal-only baseline rule** as Paper 3: baseline “detects” only **same-key overlapping validity** scenarios. For this corpus, many rows use **new** keys (`p-*`) vs baseline (`f-*`) — expect **baseline_detectable** counts for non-temporal classes to follow the Paper 3 definitions; for **`temporal_invalidation`** rows, mark baseline detectable **only** when the injected scenario actually creates overlapping windows on the **same** fact key (if the table only adds a single `p-tmp-*` fact, baseline may be **false** — log honestly).
2. Append **`baseline_simulation`** to **`real_data_lab_execution_log.jsonl`** with `total_injected: N` and per-class **`baseline_detectable` / `baseline_missed`** using the **five** logical classes where applicable (`ambiguous_case` typically treated like semantic for baseline blind unless you define a rule — default: **baseline_missed** for ambiguous unless same-key temporal overlap exists).
3. Upsert **`research.rdl.baseline.simulation`** with a one-line summary citing **`list_conflict.md`**.

---

## STEP 6 — Report

Write **`real-data-lab/research/real_data_lab_phase2_report.md`**:

- Corpus: **`list_conflict.md`**, **`N`** rows, single project
- Table of results by **`conflict_class`** (5 rows + total)
- Optional: appendix mapping **`corpus_row_id` → detection outcome**
- Injection failures and missing baseline keys

Append **`phase_complete`** to **`real_data_lab_checkpoints.jsonl`** with `total_injections: N`, `report_path`, `source: list_conflict.md`.

---

## HARD RULES

1. **Table is source of truth** for what to inject — do not invent alternate keys/bodies for scored rows unless a row is **skipped** with logged reason.
2. **MCP only** for Spirl; **log immediately** after each row.
3. **No conflict resolution** in Phase 2.
4. **Ground truth** rows must not trigger detection (`skip_conflict_check` on metadata facts).
5. If **`list_conflict.md`** is edited, re-count rows and update **STEP 2** `target_per_class` in the first `conflict_injection_start` log for that run (or derive counts from the parsed table in-code if you automate).

---

## SUCCESS CRITERIA

- [ ] All **`N`** rows from **`list_conflict.md`** (within limit) attempted; each has log line + ground truth fact (or documented skip)
- [ ] **`baseline_simulation`** + **`research.rdl.baseline.simulation`** written
- [ ] **`real_data_lab_phase2_report.md`** written
- [ ] Phase 2 **`phase_complete`** checkpoint written

---

## IF EXECUTION FAILS

Write **`phase_failed`** to **`real_data_lab_checkpoints.jsonl`** with `last_corpus_row_id`, `last_injection_number`, and resume instructions.

## Semantic trace logging upgrade

For semantic rows, call `memory_check_conflicts_v1` **before** the scored upsert with the same `kind`, `key`, `body`, and `related_facts/tags` payload you plan to inject, plus:

```json
{
  "include_semantic_trace": true
}
```

Treat the backend `semantic_trace` payload as the source of truth for semantic-path diagnostics **and semantic scoring**. Semantic rows are now **preflight-primary**; async notifications remain a transport metric. Write these fields onto every semantic-row `conflict_injected` result object in `real_data_lab_execution_log.jsonl`:

- `semantic_trace_present`: boolean
- `winning_stop_reason`: string or null
- `stage_counts`: object or null
- `semantic_trace`: full backend payload when present
- `semantic_trace_missing`: true only when the backend omitted the trace

For semantic misses, use the trace to distinguish `no_retrieval_candidates`, `predicate_overlap_blocked`, forward-NLI rejects, reverse-NLI rejects, margin failures, confidence failures, and `emitted_contradiction`.

