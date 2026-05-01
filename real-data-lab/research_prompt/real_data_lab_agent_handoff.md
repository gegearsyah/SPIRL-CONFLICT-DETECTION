# Real Data Lab — agent handoff

Use this when one agent finishes and another continues (or when splitting work across sessions).

## Before handoff

1. Append a checkpoint line to **`real-data-lab/research/real_data_lab_checkpoints.jsonl`** with `status`: `complete` or `in_progress` and a short `notes` field.
2. Ensure the last execution-log line reflects the final action taken (no batched “will write later” gaps).
3. **Never run two RDL phase scripts concurrently** (they share one JSONL). Wait for Phase 1 to finish before starting Phase 2, and so on. See **`research_prompt/README.md`** § Single writer.

## For the next agent

1. Read **`../../.spirl/config.json`** for the active real-data project id (`real_data_lab_project_id` or the key you use under `projects`).
2. Read **`real-data-lab/research/real_data_lab_checkpoints.jsonl`** from the bottom up for the relevant `phase`.
3. Scan **`real-data-lab/research/real_data_lab_execution_log.jsonl`** for the last entry for that project / phase.
4. Continue from the next step in the active phase prompt: **`real_data_lab_phase1_prompt.md`**, **`real_data_lab_phase2_prompt.md`**, or **`real_data_lab_phase3_prompt.md`**.

## Paper 3 parity

The handoff pattern matches **`research_prompt/paper3_agent_handoff.md`**; only paths and filenames change to the `real-data-lab/research/` prefix.
