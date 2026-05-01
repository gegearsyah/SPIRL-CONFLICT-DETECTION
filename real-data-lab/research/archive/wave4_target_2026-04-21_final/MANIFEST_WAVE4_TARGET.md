# Wave 4 RDL target snapshot — EMNLP 2026

This directory is the canonical **Wave 4 RDL snapshot** for the EMNLP 2026
main paper. Paired with the Wave 3 baseline at
`archive/full_redo_from_import_2026-04-15_180344Z/` it drives the
Wave 3 vs Wave 4 ablation (paper Section 5; Appendix D.2).

## Provenance

- Snapshot taken: 2026-04-21 (runner finished 2026-04-21T21:08 UTC)
- Trigger: overnight Wave 4 e2e run against the live MCP stack
  (project_id `ba546025-9c6f-438a-a661-89500d6bec7a`).
- Detector bundle at snapshot time:
  `semantic_current + dependency_v3 + constraint_v2 + temporal_v3 + w4_governance_v1`.
- Evaluation contract at snapshot time: `rdl-eval-2026-04-05-v1`.
- Wallclock: 14.7 h for 180 phase-2 rows (dominated by Supabase network +
  60 s benign notification poll, not by cascade compute — see
  `wave4_latency_breakdown.md` for the per-stage real latency).

## Known data gaps (blessed for publication, with reconstruction path)

This run was collected with the **pre-patch** RDL runner. Two fields are
affected:

1. `governance_outcome` is `null` on all 180 rows because the runner never
   extracted it from the preflight envelope. For the EMNLP 2026 Industry
   Track submission, the paper's Table 2 and Table 3 RDL governance cells
   are **reconstructed** deterministically via
   `scripts/compute_confidence_intervals.py`:`row_outcomes`, which replays
   the Neyman–Pearson likelihood-ratio selector over the per-row log using
   `final_conflict_type` and `winning_detector_plane` as inputs. The
   reconstruction uses the identical runtime thresholds
   (`governance_llr_threshold = 0.35`, `governance_ambiguous_floor = 0.15`)
   so it is equivalent to the live-runtime field up to the persisted
   log's precision. Companion TAL run data is **no longer used to
   source the RDL governance column** in the paper; the Table 2 footnote
   now points at the reconstruction path and at Appendix E.6.
   The canonical clean fix is the `RUNBOOK_R4_RDL_REPLAY.md` replay.
2. `detection_latency_ms` (top-level, post-write sync) is `null` on all
   rows because post-write detection is short-circuited whenever
   preflight already surfaced conflicts. **Real cascade latency lives
   inside `preflight_semantic.semantic_trace`** (`total_latency_ms`,
   `latency_retrieval_ms`, `latency_nli_fast_filter_ms`,
   `latency_llm_judge_total_ms`), which **was** captured. The paper's
   Section 5.7 uses those values.

Neither gap blocks publication. Both are documented in
`wave4_latency_breakdown.md` and covered by the Wave 4 runner patch in
`scripts/real_data_lab_phase2_mcp_run.py`.

## Re-running with the patched runner (optional)

If a future iteration wants a clean RDL `governance_outcome` column,
the reproducibility steps are:

```powershell
cd "SPIRAL-RESEARCH/Beyond Temporal Contradiction"
# 1. Fresh Supabase project via Spirl create-project API.
# 2. Full phase-1 import:
python scripts/real_data_lab_phase1_mcp_run.py --project-id <NEW>
# 3. Patched phase-2 (captures governance_outcome + preflight_latency_ms):
python scripts/real_data_lab_phase2_mcp_run.py --project-id <NEW>
# 4. Patched benign phase-2b (now short-circuits benign poll to 5 s
#    when preflight cleanly terminates benign — ~50 min saved):
python scripts/real_data_lab_benign_mcp_run.py --project-id <NEW>
# 5. Phase-3 report regeneration:
python scripts/real_data_lab_phase3_mcp_run.py --project-id <NEW>
```

After the re-run, archive the new snapshot as
`archive/wave4_final_<UTC>/` and update paper Table 3 + Appendix D with
the refreshed `governance_outcome` column.

## What this snapshot is used for

- **Table 2** (dual-corpus main results): RDL Wave 4 column comes from
  `real_data_lab_phase3_report.md` here.
- **Table 3** (Wave 3 vs Wave 4 ablation): Wave 4 column comes from this
  snapshot; Wave 3 column from `full_redo_from_import_2026-04-15_180344Z`.
- **Section 5.7 (Latency)**: `wave4_latency_breakdown.md` here.
- **Section 6 (Limitations)**: the dependency regression paragraph
  sources from `wave4_dependency_regression_rootcause.md` here.

## Do not overwrite

The Wave 4 runner will refuse to overwrite files under
`real-data-lab/research/` unless a fresh snapshot was taken within
60 s (Appendix E.5). This directory IS that snapshot for the Wave 4
column.
