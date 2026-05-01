# R4 RDL replay runbook

**Goal:** produce `wave4_clean_<UTC>` snapshot with `governance_outcome` and `preflight_latency_ms` non-null on all 180 rows.

**Why fresh replay:** the existing canonical snapshot `wave4_target_2026-04-21_final` was recorded before the RDL runner was patched. The `governance_outcome` logger gap leaves 0 / 180 rows with that field; the paper currently sources the `needs_review` / abstention figures from the TAL log as a workaround (disclosed in Appendix E §E.6).

**Patched runners (already on disk):**
- `scripts/real_data_lab_phase2_mcp_run.py` — now extracts `governance_outcome`, `governance_decision`, `preflight_latency_ms`, `total_cascade_latency_ms` from `preflight_raw`
- `scripts/real_data_lab_benign_mcp_run.py` — same patches + 5 s benign-poll short-circuit (cuts Phase 2b wall clock roughly 10×)

## Pre-flight checklist

- [ ] Backend FastAPI up on `http://localhost:8000` with Wave 4 flags default-on (`governance_outcome_enabled=true`, `temporal_anchor_rollback_nli_enabled=true`, `constraint_colocation_guard_enabled=true`, `voronoi_plane_selector_enabled=true`)
- [ ] Supabase project credentials in `backend/.env` pointing at a fresh (or pruned-to-empty) project
- [ ] Neo4j running, schema initialised
- [ ] OpenRouter API key + usable free-tier budget
- [ ] ML warmup completed (`warm_ml_on_startup=true` or `scripts/warm_ml_models.py` pre-run) — the first NLI call otherwise blocks ~45 s
- [ ] MCP bridge reachable

## Commands (run from the `SPIRAL-RESEARCH/Beyond Temporal Contradiction/` directory)

All runners read the project id, API base, and poll budgets from
`SPIRAL-RESEARCH/.spirl/config.json` (already populated:
`real_data_lab_project_id = 3d50dac2-ded9-454b-8b4e-0226c6be50a5`,
`api_base = http://localhost:8000`). Checkpointing is automatic — every row is
appended to `real-data-lab/research/real_data_lab_execution_log.jsonl` and
`real-data-lab/research/real_data_lab_checkpoints.jsonl`, so a crash mid-run
resumes from the last completed row on the next invocation.

If you want to replay against a brand-new clean project instead of reusing
`3d50dac2-…`, first create a new Supabase project, then update
`real_data_lab_project_id` in `.spirl/config.json` before step 2.

```powershell
# 1. (Optional) sanity-check the runner wiring without writing anything
python "scripts/real_data_lab_phase2_mcp_run.py" --precheck-only

# 2. Phase 1 — base facts (reads project id from .spirl/config.json)
python "scripts/real_data_lab_phase1_mcp_run.py"

# 3. Phase 2 — conflict injection (40 rows, ~4 h).  Resumable: if this crashes,
#    re-run the same command; it skips rows already in the execution log.
python "scripts/real_data_lab_phase2_mcp_run.py"

# 4. Phase 2b — benign injection (140 rows, ~30 min with patched short-circuit)
python "scripts/real_data_lab_benign_mcp_run.py"

# 5. Phase 3 — scoring + report regeneration
python "scripts/real_data_lab_phase3_mcp_run.py"
```

## Acceptance gate

Before archiving the snapshot as `wave4_clean_<UTC>`, verify:

```powershell
$log = "real-data-lab/research/real_data_lab_execution_log.jsonl"

# (a) governance_outcome non-null on all 180 rows
(Get-Content $log | Select-String '"governance_outcome"\s*:\s*"\w+"').Count  # expect >= 180

# (b) preflight_latency_ms non-null on all 180 rows
(Get-Content $log | Select-String '"preflight_latency_ms"\s*:\s*\d+').Count  # expect >= 180

# (c) governance_decision non-null on all 180 rows
(Get-Content $log | Select-String '"governance_decision"').Count  # expect >= 180
```

If any count < 180, do NOT archive. Debug the runner before continuing.

## Archive command

```powershell
$STAMP = [DateTime]::UtcNow.ToString("yyyy-MM-dd_HHmmssZ")
$DEST = "real-data-lab/research/archive/wave4_clean_$STAMP"
New-Item -ItemType Directory -Path $DEST | Out-Null
Copy-Item "real-data-lab/research/real_data_lab_execution_log.jsonl" $DEST
Copy-Item "real-data-lab/research/real_data_lab_mixed_report.md"      $DEST
Copy-Item "real-data-lab/research/real_data_lab_phase3_report.md"     $DEST
Copy-Item "real-data-lab/research/wave4_latency_breakdown.md"         $DEST
Copy-Item "real-data-lab/research/wave4_constants_provenance.md"      $DEST
```

Then create `$DEST/MANIFEST_WAVE4_CLEAN.md` announcing this as the new canonical snapshot and mark `wave4_target_2026-04-21_final` as superseded.

## After the replay completes

Run the downstream scripts in this order (they auto-pick-up the new log):

1. `scripts/latency_by_exit_stage.py`  (R3a — produces latency table)
2. `scripts/compute_confidence_intervals.py`  (R1a — Wilson CIs + McNemar)
3. Re-run R4f paper fold-in section (numbers update automatically from the new log)

## Budget warning

- Phase 1: ~10 min
- Phase 2: ~4 h (40 conflict rows × ~30-90 s preflight + LLM + polling)
- Phase 2b (patched): ~30 min (140 benign rows × 5 s short-circuit + overhead), was ~10 h pre-patch
- Phase 3: ~5 min

Total expected wall clock ~5 h with the patched benign runner, down from ~14.5 h on the unpatched run.

## Fallback if the replay fails

If the replay cannot be completed before the EMNLP submission deadline, the paper already supports a honest fallback:

- §Limitations discloses the logger gap
- Appendix E §E.6 footnotes the TAL-sourced governance metrics
- Appendix F (R6) shows per-row TAL governance decisions directly

The paper is not hard-blocked on R4, but the replay removes the E.6 caveat and lets the abstract headline a single-corpus `unsafe_forced_type_rate=0` claim rather than a cross-corpus one.
