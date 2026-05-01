# Paper 3 — Phase 1 & Phase 2: Experiments A vs B (Conclusion)

Generated: 2026-03-31 (after Experiment B Phase 2 completion)

This note compares **Experiment A** (`spirl_mcp_stack_v1`, canonical logs under `research/paper3_execution_log.jsonl` and `research/paper3_checkpoints.jsonl`, report `research/paper3_phase2_report.md`) with **Experiment B** (`spirl_mcp_stack_v2`, isolated logs `research/paper3_execution_log.experiment_B.jsonl` and `research/paper3_checkpoints.experiment_B.jsonl`, report `research/paper3_phase2_report.experiment_B.md`).

**Important scope note:** The checked-in `research/paper3_phase1_report.md` describes the **three Spirl projects configured for Experiment B** (UUIDs `52af2994-…`, `ec637c5a-…`, `4a847165-…`). Experiment A Phase 1 was executed against a **different trio** of project UUIDs (`24e91a29-…`, `f557ed99-…`, `17110ac4-…`); its Phase 1 metrics below are taken from `research/paper3_checkpoints.jsonl` (final `project_complete` / `phase_complete` entries), not from the current Phase 1 markdown file.

---

## Phase 1 — Corpus and graph readiness

| Metric | Experiment A (v1 projects) | Experiment B (v2 projects) |
|--------|----------------------------|------------------------------|
| Architecture label | `spirl_mcp_stack_v1` | `spirl_mcp_stack_v2` |
| Project 1 — facts / edges | 93 / 78 | 97 / 72 |
| Project 2 — facts / edges | 90 / 103 | 93 / 58 |
| Project 3 — facts / edges | 94 / 126 | 97 / 68 |
| Isolated nodes (per report) | 0 (all projects, final state) | 0 (all projects) |
| Ready for Phase 2 | Yes (checkpoints: `next_phase_prerequisites_met: true`) | Yes (`research/paper3_phase1_report.md`) |

**Takeaway:** Both arms reached a **connected, Phase-2-ready graph** on their respective project sets. Totals differ because the underlying seeded corpora and home projects are not identical between A and B; Phase 2 scripts still targeted **200 injections** with the same per-class design (50 × four classes).

---

## Phase 2 — Conflict injection and detection

Both runs completed **200 successful injections**, baseline simulation, ground-truth facts, and Phase 2 reports. Metrics below are taken verbatim from each Phase 2 report.

### By conflict class

| Class | A: preflight detected | A: notification created | B: preflight detected | B: notification created |
|-------|------------------------|-------------------------|------------------------|-------------------------|
| semantic_contradiction | 0 | 1 | 0 | 0 |
| dependency_impact | 8 | 8 | 0 | 50 |
| constraint_violation | 2 | 3 | 0 | 50 |
| temporal_invalidation | 4 | 6 | 0 | 50 |
| **Total** | **14** | **18** | **0** | **150** |

**Interpretation:** In the driver, **“preflight detected”** means `memory_upsert_fact_v1` returned a structured `detection` object with `conflicts_detected > 0`. Experiment B’s stack often surfaced conflicts in the **outbox** (`list_conflicts_v1`) while reporting **no numeric preflight hits** in the response and **null** `detection_latency_ms` in logs—so headline **notification volume** is a fairer cross-run comparison than preflight counts alone. Under that lens, **B produced far more recorded notifications (150 vs 18)** for the same injection protocol.

### By project (notification “detected” in report = notification created for that injection)

| Project slot | Experiment A (project UUID) | Detected / injected | Experiment B (project UUID) | Detected / injected |
|--------------|----------------------------|---------------------|----------------------------|---------------------|
| 1 | `24e91a29-a6db-4b8b-8fd1-7cc0c39eeaa3` | 4 / 67 | `52af2994-b03e-4236-8aea-700918461af7` | 51 / 67 |
| 2 | `f557ed99-1389-4ad5-b5be-5cc42fb94f7a` | 7 / 67 | `ec637c5a-0062-4772-b3b2-8c7727a21c99` | 50 / 67 |
| 3 | `17110ac4-017c-4a86-bc45-f643d5da18d6` | 7 / 66 | `4a847165-a8e7-4d7b-9cb2-54126a284f6c` | 49 / 66 |

### Baseline (temporal-only detector simulation)

Both experiments match the **designed** baseline split: only **temporal_invalidation** is baseline-detectable under the temporal-only rule; **50 / 200** baseline-detectable, **150** missed—consistent across A and B Phase 2 reports.

### Performance

| Metric | Experiment A | Experiment B |
|--------|--------------|--------------|
| Mean time per injection | 55.8s | 46.6s |
| Mean reported preflight latency (where present) | ~3866ms (26 points) | 0ms reported (0 points in log aggregation) |

**Takeaway:** **B was faster end-to-end per injection** in this run. Latency numbers are **not directly comparable** without aligned `detection` payloads on the v2 server (B’s report shows zero latency data points).

---

## Synthesis

1. **Phase 1:** Both experiments satisfied Phase 1 completion criteria on **different** Spirl project triples; the current `paper3_phase1_report.md` documents **B’s** projects only.
2. **Phase 2:** The **injection design and baseline accounting** are aligned (200 conflicts; same temporal-only baseline story). **Outbox notification yield was much higher on B (150 vs 18)** while **A** showed more activity in the **upsert `detection` field** (14 preflight-detected cases, 26 latency samples).
3. **Phase 3:** Both reports state **ready for Phase 3 scoring**; ground-truth keys follow `research.p3.groundtruth.{1..200}` per project rules in the driver.

## Experiment B run notes (audit)

Experiment B’s log retains earlier **`injection_failed`** / **`phase_failed`** rows from tooling issues (e.g. MCP response shape and a transient `404` on `/mcp`) before a successful **resume**; the final **`phase_complete`** checkpoint reflects **200 successful injections** and the generated `research/paper3_phase2_report.experiment_B.md`. **Experiment A canonical logs and `research/paper3_phase2_report.md` were not modified** during this work.

## References

- Experiment A Phase 2: `research/paper3_phase2_report.md`
- Experiment B Phase 2: `research/paper3_phase2_report.experiment_B.md`
- Experiment B Phase 1 (current corpus): `research/paper3_phase1_report.md`
- Experiment A Phase 1 (historical checkpoints): `research/paper3_checkpoints.jsonl`
- Driver: `scripts/paper3_phase2_mcp_run.py` (uses `paper3_phase2_artifact_paths` so B writes only `*.experiment_B.*` files)
