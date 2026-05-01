# Mixed workload — Real Data Lab (benign + conflict)

Inject **documentation-consistent benign proposals** alongside (or after) the **110 conflict** rows in `list_conflict.md`, then score **false positives** and **precision** on the combined set.

**Prerequisites:** Same MCP, project, and log shapes as [`real_data_lab_phase2_prompt.md`](real_data_lab_phase2_prompt.md) — including **60–120s async poll** after each upsert when detection is scheduled, and Neo4j-primary notification matching via `details.graph_fact_id` when needed. **Full log schema:** [`../../research_prompt/paper3_log_schema.md`](../../research_prompt/paper3_log_schema.md).

---

## Artifacts

| Artifact | Path (relative to `Beyond Temporal Contradiction/`) |
|----------|------------------------------------------------------|
| Conflict table (unchanged) | `real-data-lab/list_conflict.md` (110 rows) |
| **Benign table** | `real-data-lab/list_benign.md` (40 rows) |
| Execution log | `real-data-lab/research/real_data_lab_execution_log.jsonl` |
| Checkpoints | `real-data-lab/research/real_data_lab_checkpoints.jsonl` |
| Optional report | `real-data-lab/research/real_data_lab_mixed_report.md` |

---

## Gold labels

| `Expected Labels` (table) | `conflict_class` in logs / ground truth |
|---------------------------|----------------------------------------|
| `benign` | `benign` |

All other expected labels remain as in Phase 2 (`semanticcontradiction` → `semantic_contradiction`, etc.).

**Ground truth keys for benign rows:** `research.rdl.groundtruth.{corpus_key}` where `corpus_key` is the row ID with hyphens → underscores (e.g. `b-par-01` → `b_par_01`).

Ground truth JSON must include at minimum:

- `corpus_row_id`, `conflict_class: "benign"`, `based_on_facts[]`, `proposed_key`, `proposed_kind`, `rationale_summary`, `gold_should_alert: false`

Conflict rows keep `gold_should_alert: true` (or omit; default true for non-benign classes).

---

## When to run

**Recommended order (single project):**

1. Complete **Phase 1** and **Phase 2** (`list_conflict.md`) as today — 110 conflict injections + ground truths.
2. **Phase 2b — benign pass:** Process **`list_benign.md`** top-to-bottom with the **same** `memory_upsert_fact_v1` + logging loop as Phase 2, **without** resolving notifications.

Do **not** re-run Phase 2 conflict rows unless you reset the project.

**Alternative:** New isolated project: run Phase 1 only, then interleave rows by merging tables into a single markdown (maintain your own ordering file). The default repo does **not** ship an interleaved table; use conflict-first then benign for reproducibility.

---

## Logging (Phase 2b)

Append the same **`conflict_injection_start`** shape once per benign batch, with:

- `"action": "conflict_injection_start"` (keep action name for tooling compatibility) **or** add parallel `"action": "benign_injection_start"` if your analyzer distinguishes it — if you use the latter, duplicate any log consumers to accept both.
- `result.source`: `"real-data-lab/list_benign.md"`
- `result.mode`: `"table_driven_benign"`
- `result.target_total`: **40** (or `real_data_lab_benign_injection_limit` if you add a config cap)

For each **`conflict_injected`** line for a benign row, set:

- `corpus_row_id`: e.g. `b-par-01`
- `conflict_class`: **`benign`**
- `proposal_gold`: **`benign`** (optional duplicate for parsers)
- `gold_should_alert`: **`false`**
- `based_on_facts`, `proposed_fact_key`, `ground_truth_key` as in Phase 2

If the detector returns **`conflicts_detected` > 0** (or equivalent) for a benign upsert, that row is a **false positive** for the full policy (subject to your exact notification schema).

---

## Scoring (Phase 3 extension)

After Phase 2 + 2b:

1. **Conflict subset (110):** Keep existing per-class detection / recall metrics (detection rate on injected conflicts only).
2. **Benign subset (40):**  
   - **False positive** if any governance alert fires when `gold_should_alert` is false.  
   - **Benign true negative (TN)** if no alert.  
   - Report **FP rate** = FP / 40 (or / `N_benign` if limited).
3. **Pooled binary “alert warranted”** (optional):  
   - Positive class = conflict rows (should alert).  
   - Negative class = benign rows (should not alert).  
   - **Precision** = TP / (TP + FP), **Recall** = TP / (TP + FN), where TP/FN are on conflicts and FP/TN include benigns.

Append **`metric_computed`** lines to `real_data_lab_execution_log.jsonl` with `phase: 3`, e.g. `metric_group: "mixed_workload_fp"`, `metric_group: "mixed_workload_precision_binary"`.

Write **`real_data_lab_mixed_report.md`** (or extend **`real_data_lab_phase3_report.md`**) with a small table: conflicts (recall), benigns (FP count), pooled precision/recall if computed.

---

## HARD RULES

1. **`list_benign.md` is source of truth** for benign bodies and keys — do not paraphrase at injection time.
2. **Ground truth** facts: `skip_embedding: true`, `skip_conflict_check: true`.
3. **MCP only** for Spirl; log immediately after each row.
4. If a baseline key in “Based On Fact” is missing, log **`injection_failed`** and continue (same as Phase 2).

---

## SUCCESS CRITERIA

- [ ] All benign rows attempted; each has `conflict_injected` or `injection_failed` + ground truth (or documented skip)
- [ ] FP rate (and optional pooled precision) documented in a report
- [ ] Checkpoint `phase_complete` for benign batch with `total_injections: 40` (or actual count)

## Semantic trace on mixed runs

For rows whose gold class is `semantic_contradiction`, run a preflight `memory_check_conflicts_v1` with `include_semantic_trace: true` before the scored upsert and copy the backend trace fields into the row result:

- `semantic_trace_present`
- `winning_stop_reason`
- `stage_counts`
- `semantic_trace`
- `semantic_trace_missing`

Benign rows do not need the full trace unless the operator is running a semantic false-positive investigation.

