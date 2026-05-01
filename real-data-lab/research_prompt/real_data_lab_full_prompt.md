# Real Data Lab — full prompt (single file)

**Use when:** You want one Cursor / agent task that loads everything without chasing multiple files.

## Included content (in order)

1. **`real_data_lab_phase1_prompt.md`** — corpus verification and edges.
2. **`real_data_lab_phase2_prompt.md`** — inject all rows from **`real-data-lab/list_conflict.md`** (110 by default: semantic, dependency, constraint, temporal, ambiguous), ground truth `research.rdl.groundtruth.*`, baseline simulation; optional synthetic mode via config.
3. **`real_data_lab_mixed_workload_prompt.md`** — **Phase 2b:** benign batch from **`list_benign.md`** after Phase 2; same MCP + async poll rules.
4. **`real_data_lab_phase3_prompt.md`** — scoring, metrics, `research.rdl.results.rq*`, phase 3 report (mixed-workload FP / pooled metrics extend Phase 3 per the mixed prompt).

**Architecture (April 2026 staged semantic pipeline):** use **`../../../.spirl/config.json`** keys **`real_data_lab_architecture_doc`** / **`real_data_lab_architecture_label`** (hybrid retrieval, SparseCL, support verifier, bidirectional NLI, `include_semantic_trace`, 60–120s poll budget per architecture doc).

Always obey **`../../research_prompt/README.md`** (MCP tool names, `resolve_conflict_v1`, edge types).

**Logs only:** `real-data-lab/research/real_data_lab_execution_log.jsonl` and `real-data-lab/research/real_data_lab_checkpoints.jsonl` — not `research/paper3_*.jsonl`.

## Project id

Read from **`../../.spirl/config.json`**: prefer `real_data_lab_project_id`, or `projects.real_data_lab_project_core_platform` (or the key you set when running `import_real_data_lab_skf_mcp.py --write-config`).

## Optional injection count

Phase 2/3 use **`N`** = `real_data_lab_injection_target` in config if set, else **200**.
