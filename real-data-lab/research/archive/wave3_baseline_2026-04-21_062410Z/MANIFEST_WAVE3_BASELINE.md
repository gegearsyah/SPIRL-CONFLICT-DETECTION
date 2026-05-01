# Pre-Wave-4 RDL snapshot — EMNLP 2026 baseline

This directory is the **canonical Wave 3 baseline** for the EMNLP 2026
Wave 3 vs Wave 4 ablation (main paper Table 3; Appendix D.2). It is
preserved verbatim; do not rerun, move, or edit any file under this folder.

## Provenance

- Snapshot taken: 2026-04-21 06:24:10 UTC
- Trigger: Run A — `research/` snapshot before Wave 4 live RDL E2E
  (`wave3_baseline_2026-04-21_062410Z`; staged outside `research/` then moved
  into `archive/` to avoid recursive copy nesting).
- Detector bundle at snapshot time:
  `semantic_current + dependency_v3 + constraint_v2 + temporal_v3`
  (Wave 3; no `w4_governance_v1` suffix).
- Evaluation contract at snapshot time: `rdl-eval-2026-04-05-v1`.

## What makes this the Wave 3 baseline

This execution log predates all three Wave 4 upgrades:

1. Wave 4.1 — the NLI anchor-rollback path in
   `backend/app/services/temporal_lane.py`
   (`_detect_anchor_rollback_via_nli`).
2. Wave 4.2 — the class-of-evidence guard, constraint co-location guard,
   and the Voronoi plane selector in
   `backend/app/services/cascade_router.py` and
   `backend/app/services/constraint_lane.py`.
3. Wave 4.3 — the `governance_outcome` first-class preflight field and
   the Neyman–Pearson LLR selector in
   `backend/app/services/cascade_router.py`.

Rows in this log therefore carry the **pre-Wave-4 envelope**:
no `governance_outcome`, no `governance_decision`, and the LLR selector
is inactive. This is intentionally the shape that the main paper's
Section 4.5 calls the ``silent forced-type failure''.

## How this snapshot is used in the paper

- Main paper Table 3 (Wave 3 vs Wave 4 ablation) sources the Wave 3
  column from this snapshot and the Wave 4 column from the live
  `real-data-lab/research/real_data_lab_execution_log.jsonl`.
- Appendix D.2 (side-by-side RDL runs) enumerates each metric pair.
- Appendix E.4 (ablation runs) lists the exact config deltas between
  this snapshot and the Wave 4 target run.
- The main paper's ``unsafe forced-type rate of 1.0 on the ten RDL
  ambiguous rows'' statistic comes from this snapshot's mixed-workload
  report; it is the baseline Wave 4.3 is designed to reduce.

## Do not overwrite

The Wave 4 runner refuses to overwrite `real-data-lab/research/` files
unless a fresh snapshot has been taken in the preceding 60 seconds
(Appendix E.5). This directory is the snapshot that gates that contract
for the Wave 3 baseline column; moving or editing it invalidates the
published ablation.
