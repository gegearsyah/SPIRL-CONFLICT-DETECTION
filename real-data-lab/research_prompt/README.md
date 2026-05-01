# Real Data Lab — research prompts

Prompts for **multiagent / MCP runs on the real-data-lab corpus**, parallel to **`Beyond Temporal Contradiction/research_prompt/`** (Paper 3).

## Repo layout

All paths below are relative to **`Beyond Temporal Contradiction/`** (SPIRAL-RESEARCH → `Beyond Temporal Contradiction/`).

| Area | Location |
|------|----------|
| **This prompt pack** | `real-data-lab/research_prompt/` |
| **Logs & checkpoints** | `real-data-lab/research/` |
| **SKF + notes** | `real-data-lab/*.skf.json`, `*.md` |
| **Full MCP tool / enum rules** | `research_prompt/README.md` (reuse; do not duplicate mistakes) |
| **Log entry field definitions** | `research_prompt/paper3_log_schema.md` + `real_data_lab_log_schema.md` (paths + naming) |
| **Spirl config** | `../.spirl/config.json` |

## File structure

```
real-data-lab/research_prompt/
├── README.md                        # This file
├── real_data_lab_log_schema.md     # Where logs live + naming for this track
├── real_data_lab_mcp_semantic_pipeline_prompt.md  # End-to-end: MCP new project → Phase 1 → semantic → benign FP
├── real_data_lab_phase1_prompt.md  # Phase 1: corpus verification / edges
├── real_data_lab_phase2_prompt.md  # Phase 2: conflict injection + baseline simulation
├── real_data_lab_phase3_prompt.md  # Phase 3: scoring, metrics, RQ facts, report
├── real_data_lab_mixed_workload_prompt.md  # Phase 2b + mixed metrics: list_benign.md after conflicts
├── real_data_lab_semantic_validation_prompt.md  # Semantic-contradiction-only track (before full Phase 2)
├── real_data_lab_agent_handoff.md  # Handoff between phases or agents
└── real_data_lab_full_prompt.md    # Single-file bundle for one-shot agents
```

## End-to-end MCP pipeline (new project → Phase 1 → semantic → benign)

Single checklist (project pinned in **`.spirl/config.json`**, no Hoyer setup in-repo): **`real_data_lab_mcp_semantic_pipeline_prompt.md`**.

## Semantic validation track (optional, recommended first)

To validate **semantic contradiction** only (40 `c-sem-*` rows + focused benign), use **`real_data_lab_semantic_validation_prompt.md`**, corpus slices **`list_conflict_semantic_only.md`** / **`list_benign_semantic_focus.md`**, and scripts **`real_data_lab_semantic_conflict_mcp_run.py`** then **`real_data_lab_semantic_benign_mcp_run.py`**. Logs: **`real_data_lab_semantic_execution_log.jsonl`** (phases 4–5) by default, or **per-experiment suffixed** files when using **`--hoyer`** / **`--experiment-id`** (e.g. four Hoyer runs). Sequential driver: **`real_data_lab_semantic_hoyer_sweep.py`**. Shared resolver: **`real_data_lab_semantic_experiment.py`**.

## Execution order

**Phase 1 → Phase 2 → Phase 3** (same cadence as Paper 3).  
**Optional:** **Phase 1 → semantic validation (scripts above) → Phase 2 → …** when you want to tune recall/precision on the semantic path before the full 110-row table.  
**Optional mixed workload:** after Phase 2, run **Phase 2b** per **`real_data_lab_mixed_workload_prompt.md`** using **`real-data-lab/list_benign.md`**, then extend Phase 3 with FP / pooled precision (see that prompt).

### Single writer (important)

Phases are **separate scripts**, not one combined job: `real_data_lab_phase1_mcp_run.py`, then `real_data_lab_phase2_mcp_run.py`, then `real_data_lab_benign_mcp_run.py`, then `real_data_lab_phase3_mcp_run.py`. They all append to the **same** `real-data-lab/research/real_data_lab_execution_log.jsonl`. **Do not run two of these at the same time** (including Phase 1 on a new project while Phase 2 is still running on an old project): lines interleave by timestamp and it looks like “Phase 1 and Phase 2 together,” corrupts analysis, and Phase 2 will refuse to continue if it sees `phase: 2` rows for a different `project` id. The scripts acquire **`real_data_lab_pipeline.lock`** automatically; use **`--ignore-pipeline-lock`** only when you are sure nothing else is writing. **Pause mid-run:** create **`real-data-lab/research/real_data_lab_pause.flag`** (empty file); Phase 1 (edge loop) and Phase 2 (injection loop) stop cooperatively — delete the flag before re-running.

Reports and JSONL live under **`real-data-lab/research/`**. For parallel experiments, use suffixed log files (see **`real_data_lab_log_schema.md`**).

**Optional config (`.spirl/config.json`):**

| Key | When |
|-----|------|
| **`real_data_lab_phase2_mode`** | **`"synthetic"`** → Paper 3–style random injections; omit or any other value → **default: table-driven** from **`real-data-lab/list_conflict.md`**. |
| **`real_data_lab_injection_limit`** | Table-driven only: process at most this many rows from the top of the table (smoke test). |
| **`real_data_lab_conflict_list_path`** | Override path to the markdown table (relative to **`Beyond Temporal Contradiction/`**). |
| **`real_data_lab_injection_target`** | Synthetic mode only: target injection count (default **200**). |
| **`real_data_lab_semantic_conflict_list_path`** | Semantic track: override conflict table path (relative to **`Beyond Temporal Contradiction/`**). |
| **`real_data_lab_semantic_benign_list_path`** | Semantic track: override benign focus table path. |
| **`real_data_lab_semantic_injection_limit`** | Semantic track: cap rows from the semantic-only conflict table. |

## Spirl MCP reminders

Use the same tool IDs and constraints as Paper 3 (`list_facts_v1`, `list_conflicts_v1`, `resolve_conflict_v1` with `resolution` enum, `related_to` not `validates`, etc.). See **`research_prompt/README.md`** tables.
