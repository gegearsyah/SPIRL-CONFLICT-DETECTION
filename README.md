# Beyond Temporal Contradiction — research artifacts (publication bundle)

Self-contained slice of the **SPIRAL-RESEARCH** monorepo intended to become its **own GitHub repository**: Real Data Lab (RDL), Trusted ADR Lab (TAL), Paper~3 / Experiment~D research harness, offline cascade **state-orchestration-lab**, and all **Python / PowerShell** drivers we used to score runs.

This is **not** the full Spirl product (no `backend/` FastAPI tree here). Pair this repo with the paper and your own Spirl-compatible API + knowledge graph to replicate the *methodology*; swap in your project UUIDs and corpus.

---

## Contents

| Path | Purpose |
|------|--------|
| [`architecture/`](architecture/README.md) | How the offline ablation maps to the cascade; link to Appendix~G narrative + provenance doc |
| [`state-orchestration-lab/`](state-orchestration-lab/README.md) | **Portable** Neo4j-oriented cascade + ablation sweep + log replay |
| [`real-data-lab/`](real-data-lab/) | RDL lists, prompts, **all shipped execution logs / reports / `research/archive/` snapshots** |
| [`trusted-adr-lab/`](trusted-adr-lab/README.md) | TAL prompts, reports, row dumps, archives |
| [`research/`](research/) | Legacy Paper~3 logs, SKF seeds, experiment D artifacts (`paper3_*.jsonl`, `trusted_adr/`, …) |
| [`scripts/`](scripts/) | MCP runners (`real_data_lab_*`, `trusted_adr_lab_*`), stats (`compute_confidence_intervals.py`, `latency_by_exit_stage.py`), E2E drivers (`run_*_e2e.ps1`) |

---

## Quick start (after you `git init` here)

1. **Python 3.11+** recommended. Install script deps as needed (many scripts only use stdlib + `urllib`; MCP runners may need your environment’s HTTP stack).

2. **Spirl config**  
   Copy [`.spirl/config.example.json`](.spirl/config.example.json) → `.spirl/config.json` and fill:
   - `api_base` (your Spirl API)
   - `real_data_lab_project_id` / `trusted_adr_lab_project_id` (or `projects.*` keys used by `paper3_spirl_config.py`)

3. **RDL replay / fresh run**  
   Read [`real-data-lab/research/RUNBOOK_R4_RDL_REPLAY.md`](real-data-lab/research/RUNBOOK_R4_RDL_REPLAY.md). Typical order (from **repo root**):

   ```powershell
   cd scripts
   python real_data_lab_phase1_mcp_run.py
   python real_data_lab_phase2_mcp_run.py
   python real_data_lab_benign_mcp_run.py
   python real_data_lab_phase3_mcp_run.py
   ```

   Or: `.\run_real_data_lab_e2e.ps1` (check paths inside; cwd is usually `scripts/`).

4. **TAL**  
   See [`trusted-adr-lab/README.md`](trusted-adr-lab/README.md) — e.g. `python experiment_d_trusted_adr_track.py --lab-root ../trusted-adr-lab` from repo root, or `.\run_trusted_adr_lab_e2e.ps1` from `scripts/`.

5. **Offline cascade ablation**  
   `cd state-orchestration-lab` and follow its README (`run_ablation_sweep.py`, `replay_governance_log.py`, …).

---

## Layout note for contributors

`scripts/paper3_paths.py` treats **this repo root** as `btc_root()` (parent of `scripts/`).  
Optional: set `SPIRAL_REPO_ROOT` to a full **SPIRAL-RESEARCH** checkout if you want `.cursor/mcp.json` and `.spirl/config.json` to resolve there instead.

---

## Size / hygiene before `git push`

`real-data-lab/research/archive/` may contain **nested duplicate snapshots** from historical copy operations in the monorepo. For a clean public repo you may want to:

- Keep **canonical** snapshots only (e.g. `wave4_target_2026-04-21_final`, `pre_v3b_*`, `snapshot_2026-04-24_*`), or  
- Use **Git LFS** for large `*.jsonl` logs, or  
- Ship **reports-only** plus a Zenodo archive for raw logs.

This bundle is a **faithful export** of what lived under `Beyond Temporal Contradiction/` at export time.

---

## Citation

Point readers to your EMNLP / arXiv paper and cite this repository for artifacts and reproduction scripts.
