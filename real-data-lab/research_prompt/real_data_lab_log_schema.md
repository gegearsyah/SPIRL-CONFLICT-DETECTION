# Real Data Lab — execution log locations

## Purpose

Real-data-lab runs use the **same JSONL entry shapes and action types** as Paper 3 so you can reuse tooling and mental model. The canonical field definitions and examples live in:

**[`../../research_prompt/paper3_log_schema.md`](../../research_prompt/paper3_log_schema.md)**

This file only pins **where** agents write logs for the real-data track so they never overwrite `research/paper3_*.jsonl`.

## Log files (default)

Relative to **`Beyond Temporal Contradiction/`**:

```
real-data-lab/research/real_data_lab_execution_log.jsonl
real-data-lab/research/real_data_lab_checkpoints.jsonl
```

Reports (optional):

```
real-data-lab/research/real_data_lab_phase1_report.md
real-data-lab/research/real_data_lab_phase2_report.md
real-data-lab/research/real_data_lab_phase3_report.md
```

## Multiple experiments in parallel

If you need separate runs (different SKF imports or hypotheses), copy the default files under `real-data-lab/research/` with a suffix, for example:

- `real_data_lab_execution_log.slice_a.jsonl`
- `real_data_lab_checkpoints.slice_a.jsonl`

Document the active pair at the top of your run prompt or in a one-line README next to the files.

## Resume protocol

Same as Paper 3: read the checkpoints file for this run, find last `phase` / `status`, then continue from `real_data_lab_execution_log` for that run.

## Phase 2 table-driven fields

When using **`real-data-lab/list_conflict.md`**, Phase 2 **`conflict_injected`** (and related) lines may include **`corpus_row_id`**, **`based_on_facts`**, **`proposed_fact_key`**, and **`ground_truth_key`** aligned with **`real_data_lab_phase2_prompt.md`**.

## Semantic trace fields (diagnostic extension)

For semantic-row log entries, `result` may additionally include:

- `semantic_trace_present: boolean`
- `winning_stop_reason: string | null`
- `stage_counts: object | null`
- `semantic_trace: object` (full backend diagnostic trace)
- `semantic_trace_missing: boolean`

`winning_stop_reason` should come directly from the backend trace and typically be one of:

- `no_retrieval_candidates`
- `sparsecl_filtered`
- `predicate_overlap_blocked`
- `forward_nli_non_contradiction`
- `forward_margin_failed`
- `forward_confidence_failed`
- `reverse_nli_non_contradiction`
- `reverse_margin_failed`
- `reverse_confidence_failed`
- `emitted_contradiction`

