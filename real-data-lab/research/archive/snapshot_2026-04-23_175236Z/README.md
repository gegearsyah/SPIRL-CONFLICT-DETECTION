# Real Data Lab — execution artifacts

This folder mirrors **`Beyond Temporal Contradiction/research/`** but is **only for runs against real corpus SKF / Spirl projects** imported from `real-data-lab/` (for example `Project Core Platform.skf.json`).

Use it so Paper 3 synthetic runs (`../research/paper3_*.jsonl`) stay separate from real-data experiments.

## Spirl server: semantic retrieval vs Phase 2 pollution

Phase 2 proposes facts under **`p-*`** keys and stores harness metadata under **`research.*`** (for example `research.rdl.groundtruth.*`). Those rows are embedded like any other fact. If the semantic / dense-retrieval stage does **not** filter them out, **earlier injections can be retrieved as candidates for later rows**, which biases preflight traces, NLI pairing, and stop reasons (cross-injection pollution).

**Mitigation (Spirl backend environment, not this repo’s JSON):** set

`SEMANTIC_RETRIEVAL_EXCLUDED_KEY_PREFIXES=p-,research.`

so keys starting with `p-` or `research.` are excluded from semantic retrieval candidates. (Use the delimiter your Spirl build expects if it differs from comma-separated prefixes.) The same value is mirrored under **`recommended_spirl_env_SEMANTIC_RETRIEVAL_EXCLUDED_KEY_PREFIXES`** in **`.spirl/config.json`** for operators; the harness scripts do not read it—it is documentation only.

Paper~3 interim numbers for the **live** RDL trace (async notification hit rate on the first nine semantic injections) are summarized in **`rdl_interim_paper_stats.json`**; regenerate that file after you extend Phase~2. Offline engine replay of the same log uses **`../state-orchestration-lab/replay_governance_log.py`** with `--basis-path` to the project SKF.

## Run order (same project)

After **Phase 1** completes, run **Phase 2**, then **Phase 2b**, then **Phase 3** if you have not already (one harness at a time). From **`Beyond Temporal Contradiction/scripts/`**:

1. `python real_data_lab_phase2_mcp_run.py` — `list_conflict.md` (110 rows)
2. `python real_data_lab_benign_mcp_run.py` — `list_benign.md` (40 rows) + mixed metrics
3. `python real_data_lab_phase3_mcp_run.py` — report + `research.rdl.results.rq*`

Or use **`../../scripts/run_real_data_lab_e2e.ps1`** for import → 1 → 2 → 2b → 3 in one go.

## Semantic scoring + polling policy

- Semantic rows are now **preflight-primary**: `memory_check_conflicts_v1(... include_semantic_trace=true, expected_anchor_keys=based_on_facts)` is the canonical semantic detector output for RDL scoring.
- Async notifications remain a **transport / matcher metric**. They are still logged, but they no longer decide semantic correctness when semantic preflight already returned a terminal answer.
- Semantic rows fast-exit by policy: terminal semantic preflight miss → **0s** async poll, preflight-detected semantic hit → **15s** short poll, missing/errored semantic preflight → full fallback poll budget.

## Default log files (JSONL, append-only)

| File | Purpose |
|------|---------|
| `real_data_lab_execution_log.jsonl` | Structured actions (same entry shape as Paper 3; see `../research_prompt/real_data_lab_log_schema.md`) |
| `real_data_lab_checkpoints.jsonl` | Phase / run boundaries for resume |
| `real_data_lab_semantic_execution_log.jsonl` | **Semantic validation track only** (phases 4–5; see `../research_prompt/real_data_lab_semantic_validation_prompt.md`) |
| `real_data_lab_semantic_checkpoints.jsonl` | Checkpoints for the semantic track |

## Optional layout

- **`archive/`** — timestamped copies of logs or reports before a big redo (same idea as `research/archive/`).

## Mixed workload (benign + conflict)

- **Benign table:** **`../list_benign.md`** (40 documentation-consistent proposals; gold label `benign`).
- **Prompt:** **`../research_prompt/real_data_lab_mixed_workload_prompt.md`** — Phase 2b after Phase 2, then extended Phase 3 metrics (FP rate, optional pooled precision).
- **Manifest:** **`mixed_workload_manifest.json`** — expected counts and run order.
- **Row counts:** `python ../../scripts/real_data_lab_table_stats.py` from repo root (pass `--btc-root` if needed).

## Related paths

- Prompts: **`../research_prompt/`** (Phases 1–3: `real_data_lab_phase{1,2,3}_prompt.md`; mixed: `real_data_lab_mixed_workload_prompt.md`)
- Import helper: **`../../scripts/import_real_data_lab_skf_mcp.py`**
- Spirl project id: **`../../.spirl/config.json`** (`real_data_lab_project_id` or `projects.real_data_lab_project_core_platform` after `--write-config`)
- Phase 2 corpus: default is **`../list_conflict.md`** (110 scripted rows); optional **`real_data_lab_injection_limit`**, **`real_data_lab_conflict_list_path`**, **`real_data_lab_phase2_mode`: `"synthetic"`** — see `research_prompt/real_data_lab_phase2_prompt.md`
