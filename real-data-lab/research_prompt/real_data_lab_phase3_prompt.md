# Phase 3 — Real Data Lab: Scoring, Metrics and Analysis
## Multiagent prompt with structured logging (**one** Spirl project)

**Full scoring logic:** [`../../research_prompt/paper3_phase3_prompt.md`](../../research_prompt/paper3_phase3_prompt.md)  
This file fixes **artifact paths**, **ground-truth / RQ key prefixes**, and **single-corpus** reporting (no three-project variance table).

---

## Artifact paths (fixed for Real Data Lab)

Unless you use suffixed log files (see [`real_data_lab_log_schema.md`](real_data_lab_log_schema.md)):

| Variable | Path (relative to `Beyond Temporal Contradiction/`) |
|----------|------------------------------------------------------|
| **EXEC_LOG** | `real-data-lab/research/real_data_lab_execution_log.jsonl` |
| **CHECKPOINTS** | `real-data-lab/research/real_data_lab_checkpoints.jsonl` |
| **PHASE3_REPORT** | `real-data-lab/research/real_data_lab_phase3_report.md` |

Phase 3 appends rows with `"phase": 3` to **EXEC_LOG** (same file as Phases 1–2 for this track).

**Injection count `N`:** Read Phase 2 **`phase_complete`** checkpoint in **CHECKPOINTS** for `total_injections`, or count deduped **`conflict_injected`** lines in **EXEC_LOG** (`phase === 2`). Use **`N`** everywhere Paper 3 says **200**.

**Table-driven Phase 2 (`list_conflict.md`):** When Phase 2 **`conflict_injection_start`** has `result.mode: "table_driven"`, **`N`** is typically **110** (unless `real_data_lab_injection_limit` was used). Prefer deduping **`conflict_injected`** rows by **`corpus_row_id`** when present (else by **`injection_number`**). Ground truth keys look like **`research.rdl.groundtruth.c_sem_01`** (hyphens → underscores). **`ambiguous_case`** is a **fifth** expected class — extend confusion-matrix / summary tables if Paper 3 templates only list four classes (add a row or an “ambiguous” subsection).

---

## MCP-FIRST RULE (CRITICAL)

Same as Paper 3 Phase 3: **MCP only**, Streamable HTTP (not SSE).

---

## BEFORE YOU START

### Resume

Read **CHECKPOINTS** for `"phase": 3` — same table as [`paper3_phase3_prompt.md`](../../research_prompt/paper3_phase3_prompt.md) § BEFORE YOU START.

### Prerequisites

- [ ] **CHECKPOINTS** contains `"phase": 2, "checkpoint_type": "phase_complete", "status": "complete"`
- [ ] **EXEC_LOG** contains at least **`N`** successful **`conflict_injected`** rows (dedupe by `injection_number`, keep latest)
- [ ] Spirl contains **`research.rdl.baseline.simulation`**
- [ ] Count of **current** **`research.rdl.groundtruth.*`** facts matches successful injections (or document shortfall)

**Project id:** from **`../../.spirl/config.json`** — same single real-data-lab project as Phases 1–2.

---

## Ground truth and RQ keys (Real Data Lab)

| Purpose | Key prefix / keys |
|---------|-------------------|
| Ground truth | `research.rdl.groundtruth.*` |
| RQ answers | `research.rdl.results.rq1`, `research.rdl.results.rq2`, `research.rdl.results.rq3` |

---

## STEPS 1–5 — Same as Paper 3 Phase 3

Execute [**`paper3_phase3_prompt.md`**](../../research_prompt/paper3_phase3_prompt.md) Steps **1** through **5** with these substitutions:

1. Use **EXEC_LOG**, **CHECKPOINTS**, **PHASE3_REPORT** from the table above (not `paper3_experiment_id` suffix rules unless you deliberately use suffixed Real Data Lab files).
2. In **Step 2**, filter facts with keys starting **`research.rdl.groundtruth.`**
3. In **Step 2b** `ground_truth_read` log, set **`by_project`** to a single entry: `{ "{project_id}": {count} }` (or omit `by_project` and put total in `total_records` only — be consistent in the report).
4. **`agent_id`:** e.g. **`rdl_phase3_judge_agent`**
5. Replace every **`200`** / **“200 conflicts”** with **`N`**.

Detection rules (`spirl_detected`, `async_observed`, `preflight_check`, dedupe of `conflict_injected` rows) are **unchanged** from Paper 3.

---

## STEP 6 — Cross-project consistency → single corpus

Paper 3 Step 6 compares three projects. For Real Data Lab, **skip** multi-project F1 statistics.

Append one **EXEC_LOG** entry:

```json
{
  "timestamp": "{ISO_NOW}",
  "phase": 3,
  "agent_id": "rdl_phase3_judge_agent",
  "action": "metric_computed",
  "project": "{project_id}",
  "metric_group": "cross_project_consistency",
  "result": {
    "note": "Real Data Lab — single corpus; no cross-project variance.",
    "overall_F1": {f1},
    "corpus": "real_data_lab"
  }
}
```

---

## STEP 7 — RQ answers

Upsert **`research.rdl.results.rq1`**, **`research.rdl.results.rq2`**, **`research.rdl.results.rq3`** with the **same** RQ intents as Paper 3, citing **your** **`N`**-conflict corpus.

Log **`rq_answer_written`** rows to **EXEC_LOG** with `result.fact_key` set to those keys.

---

## STEP 8 — Report (**PHASE3_REPORT**)

Generate **`real-data-lab/research/real_data_lab_phase3_report.md`** from the Paper 3 Phase 8 template with these edits:

- Title / header: **Real Data Lab** + single project name/id.
- **Corpus:** **`N`** conflicts, **one** project.
- **Table 4 (cross-project):** Replace with a short subsection: **“Single corpus — cross-project table N/A”** and cite **`overall_F1`** from Step 6.
- **Table 6** and any **“200”** totals: use **`N`**.
- **Limitations:** Add that the corpus is **one** real imported graph (plus injected conflicts), not three synthetic domains — generalisation claims should be toned down accordingly.
- **RQ Answers** section: pull text from **`research.rdl.results.rq1..rq3`**.

Append **`phase_complete`** for phase 3 to **CHECKPOINTS** with `report_path` pointing to **PHASE3_REPORT**.

---

## HARD RULES

Same as [`paper3_phase3_prompt.md`](../../research_prompt/paper3_phase3_prompt.md) § HARD RULES, except:

- Resolve paths from the **Real Data Lab** table at the top (not `paper3_experiment_id`).
- Do not claim three-project consistency unless you actually ran three projects.

---

## SUCCESS CRITERIA

- [ ] **EXEC_LOG** / **CHECKPOINTS** / **PHASE3_REPORT** paths correct for this track
- [ ] Ground truth **`research.rdl.groundtruth.*`** ingested into scoring lists
- [ ] Confusion matrices, improvement ratios, latency block (§5) computed; **Step 6** single-corpus note logged
- [ ] **`research.rdl.results.rq1..rq3`** written
- [ ] **PHASE3_REPORT** on disk; phase 3 **`phase_complete`** checkpoint written

---

## IF EXECUTION FAILS

Write **`phase_failed`** to **CHECKPOINTS** (same pattern as Paper 3 Phase 3).
