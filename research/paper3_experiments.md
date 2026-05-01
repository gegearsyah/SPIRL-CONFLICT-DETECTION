# Paper 3 — experiment registry

Use this file to record what each run label means. Values in `.spirl/config.json` drive where the Phase 2 MCP driver writes logs and reports.

| Experiment | `paper3_experiment_id` | `paper3_architecture_label` (example) | Phase 2 execution log | Phase 2 checkpoints | Phase 2 report |
|------------|------------------------|----------------------------------------|------------------------|---------------------|----------------|
| **A** | `A` | `spirl_mcp_stack_v1` | `research/paper3_execution_log.jsonl` | `research/paper3_checkpoints.jsonl`* | `research/paper3_phase2_report.md` |
| **B** | `B` (or any id other than `A`) | Set before run (e.g. `spirl_stack_v2`) | `research/paper3_execution_log.experiment_B.jsonl` | `research/paper3_checkpoints.experiment_B.jsonl` | `research/paper3_phase2_report.experiment_B.md` |

\*Phase 1 `phase_complete` and shared milestones stay in `research/paper3_checkpoints.jsonl` for all experiments. The Phase 2 driver always checks Phase 1 against that canonical file only.

## Experiment A (completed)

- **Status:** Phase 2 complete (200 injections); report `paper3_phase2_report.md` dated 2026-03-31.
- **Stack:** Spirl MCP as configured in this repo at time of run (`spirl_mcp_stack_v1` in config).

## Experiment B (checklist)

**Config (this checkout):** `paper3_experiment_id` **B**, `paper3_architecture_label` **spirl_mcp_stack_v2** — Phase 2 log: `paper3_execution_log.experiment_B.jsonl`, tee log: `paper3_phase2_experiment_B_run.log`.

1. Provision the new Spirl / graph / embedding stack and obtain project UUIDs.
2. Update `.cursor/mcp.json` to the new MCP endpoint (and auth if needed).
3. Update `.spirl/config.json`: `paper3_experiment_id` → `B`, `paper3_architecture_label` → your label, `projects` / `api_base` / `paper3_fact_kind` as required by the server.
4. Ensure Phase 1 is complete in Spirl for those projects (canonical checkpoint in `paper3_checkpoints.jsonl` still applies).
5. Run `python scripts/paper3_phase2_mcp_run.py`; artifacts land in the suffixed `experiment_B` files.
6. Record any protocol tweaks here so A and B stay comparable.

## JSONL `experiment` field

From the updated Phase 2 driver, each Phase 2 line includes:

```json
"experiment": { "id": "A", "architecture_label": "spirl_mcp_stack_v1" }
```

Legacy lines in Experiment A’s log may omit `experiment`; the driver treats those as experiment **A** when resuming or reporting.
