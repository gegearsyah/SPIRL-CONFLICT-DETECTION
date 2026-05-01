# Real Data Lab — MCP pipeline: new project → Phase 1 → semantic contradictions → benign FP

Use this when you want **one** Spirl project, **MCP only**, in this order:

1. **Create / import** the corpus project (SKF) and **pin** its UUID in the repo.  
2. **Phase 1** — baseline, edges, graph verification.  
3. **Semantic contradiction** track — 40 `c-sem-*` injections (`list_conflict_semantic_only.md`).  
4. **Benign FP** track — `list_benign_semantic_focus.md` on the **same** project.

**Hoyer λ (semantic path):** set the coefficient on the **Spirl server** to match what you log. For this lab we **standardize on λ = 0.25** — prior runs at **0.20** behaved poorly for recall / stability, so do not use 0.20 in new sweeps.

- **Ground truth** for scored rows: `research.rdl.semantic_gt.*` (see `real_data_lab_semantic_validation_prompt.md`).
- **Provenance in logs:** pass `--hoyer 0.25` on both semantic scripts so JSONL and reports use experiment id `hoyer_0p25` and filenames like `real_data_lab_semantic_execution_log.hoyer_0p25.jsonl`.
- **Fresh graph per λ (recommended):** import a clean project or clear prior `p-*` / `p-sben-*` facts before comparing λ values.

Sweep (omits 0.20 by default):

```bash
python real_data_lab_semantic_hoyer_sweep.py --hoyers 0.25
# or full comparison grid: 0.10, 0.15, 0.25
```

---

## 1 — Pin the Spirl project (single source of truth)

All scripts read **`SPIRAL-RESEARCH/.spirl/config.json`**:

- `real_data_lab_project_id` **or**
- `projects.real_data_lab_project_core_platform`

**Do not hardcode UUIDs in this prompt’s execution** — always use the id written by the import step.

### 1a — New project + SKF import via MCP

From `Beyond Temporal Contradiction/scripts/` (Bearer token from `.cursor/mcp.json` → `mcpServers.spirl`, same as other lab scripts):

```bash
python import_real_data_lab_skf_mcp.py --write-config
```

This creates a project (unless you pass `--project-id` / `--no-create`), runs MCP **`import_skf`** for `real-data-lab/Project Core Platform.skf.json`, and updates `.spirl/config.json` with the new id.

Optional: `--skf PATH`, `--api-base`, `--mcp-url` if not default.

### 1b — Confirm pin

Open `.spirl/config.json` and note `real_data_lab_project_id`. Optional sanity check: MCP **`get_pm_context`** with that `project_id`.

---

## 2 — Phase 1 (corpus + edges)

**Prerequisite:** `real-data-lab/research/rdl_phase1_edges_plan.json` exists (regenerate if needed):

```bash
python build_rdl_phase1_edges.py
```

Run Phase 1:

```bash
python real_data_lab_phase1_mcp_run.py
```

**Artifacts:** `real-data-lab/research/real_data_lab_execution_log.jsonl`, `real_data_lab_checkpoints.jsonl`, `real_data_lab_phase1_report.md` (main RDL track — not the semantic-only logs).

**Checkpoint:** Phase 1 `phase_complete` in `real_data_lab_checkpoints.jsonl` before semantic scripts.

---

## 3 — Semantic contradiction injections (40 rows)

Uses the **same** pinned `project_id`. With **`--hoyer 0.25`** (recommended), logs use the `.hoyer_0p25` artifact set; omit `--hoyer` only for the legacy unsuffixed filenames.

```bash
python real_data_lab_semantic_conflict_mcp_run.py --hoyer 0.25
```

**Corpus:** `real-data-lab/list_conflict_semantic_only.md`.  
**Artifacts:** with `--hoyer 0.25`, files are suffixed `.hoyer_0p25` (e.g. `real_data_lab_semantic_execution_log.hoyer_0p25.jsonl`); omit `--hoyer` only for the unsuffixed default track.

Optional: `--injection-limit N`, `--poll-max-wait SEC`.  
Optional: `--experiment-id …` if you need a custom id instead of `hoyer_0p25`.

---

## 4 — Benign FP (semantic-focused)

**Same** `project_id` and **same** experiment flags as step 3 (if any):

```bash
python real_data_lab_semantic_benign_mcp_run.py --hoyer 0.25
```

**Corpus:** `real-data-lab/list_benign_semantic_focus.md`.  
**Artifacts:** appends phase **5** to the same Hoyer-tagged semantic execution log; `real_data_lab_semantic_validation_report.hoyer_0p25.md` when using `--hoyer 0.25`.

---

## MCP rules (unchanged)

- **MCP only** (Streamable HTTP), same tool IDs as `research_prompt/README.md` / `real_data_lab_phase2_prompt.md`.  
- Retry policy and async poll semantics: `real_data_lab_semantic_validation_prompt.md`.

---

## Quick reference (repo root = `SPIRAL-RESEARCH`)

| Step | Script | Config pin |
|------|--------|------------|
| Import + pin | `Beyond Temporal Contradiction/scripts/import_real_data_lab_skf_mcp.py --write-config` | writes `.spirl/config.json` |
| Phase 1 | `real_data_lab_phase1_mcp_run.py` | reads `real_data_lab_project_id` |
| Semantic conflicts | `real_data_lab_semantic_conflict_mcp_run.py` | same |
| Benign FP | `real_data_lab_semantic_benign_mcp_run.py` | same |

---

## Related prompts

| Doc | Use when |
|-----|----------|
| [`real_data_lab_semantic_validation_prompt.md`](real_data_lab_semantic_validation_prompt.md) | Semantic track details, logs, optional experiment suffixes |
| [`real_data_lab_phase1_prompt.md`](real_data_lab_phase1_prompt.md) | Phase 1 agent checklist |
| [`real_data_lab_phase2_prompt.md`](real_data_lab_phase2_prompt.md) | Full 110-row track (after this pipeline if needed) |
