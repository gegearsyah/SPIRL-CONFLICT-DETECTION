# Trusted ADR Lab

Sibling layout to [`../real-data-lab/`](../real-data-lab/): prompts, append-only logs, reports, and snapshots live **under this folder** so Experiment D style work does not mix with the live RDL benchmark.

**Shorthand:** **TAL** = Trusted ADR Lab (`trusted-adr-lab/`).

For the paper claim map, start at [`../PAPER_RESULTS_GUIDE.md`](../PAPER_RESULTS_GUIDE.md).

## Paper-facing status

TAL is a small out-of-distribution ADR probe: 18 rows total (8 typed conflicts, 4 ambiguous rows, 6 benign rows). It has no dependency-edge substrate, so `dependency_impact` is `n/a`.

The paper's TAL table should be checked against the main paper TAL paragraph, the raw execution log, and the materialized row files here:

| Artifact | Role |
| --- | --- |
| [`research/trusted_adr_lab_execution_log.jsonl`](research/trusted_adr_lab_execution_log.jsonl) | Raw TAL execution log. |
| [`research/trusted_adr/trusted_*_rows.jsonl`](research/trusted_adr/) | Materialized TAL row data with source paths/sections. |
| [`research/trusted_adr_lab_confusion_matrix.md`](research/trusted_adr_lab_confusion_matrix.md) | Generated confusion matrix companion. |
| [`research/trusted_adr_lab_mixed_report.md`](research/trusted_adr_lab_mixed_report.md) | Generated pipeline report; useful, but not canonical if it disagrees with the main paper text and raw execution log. |

Known paper-facing interpretation:

- TAL binary F1 is lower than RDL; this is reported as a portability stress test, not as parity.
- Three benign TAL rows route to `needs_review`; strict scoring counts them as false positives, while abstention-aware scoring treats them as deferrals rather than typed commits.
- One of four ambiguous TAL rows routes to `needs_review`; three under-route to `benign`.
- No ambiguous TAL row is forced into a committed typed conflict label.

### How to tell the agent (same idea as “run RDL E2E”)

Use any of these; they mean the same pipeline:

- **“Run TAL E2E”** or **“Run Trusted ADR Lab from start to finish”**

The agent should `cd` to `Beyond Temporal Contradiction/scripts` and run `.\run_trusted_adr_lab_e2e.ps1` (or the equivalent `python experiment_d_trusted_adr_track.py --lab-root ../trusted-adr-lab`).

Optional before a redo: **“Archive TAL”** → `.\archive_btc_lab_research.ps1 -LabFolder trusted-adr-lab` from `scripts/`.

Note: TAL today is a **single offline materialization** (Experiment D artifacts), not the multi-phase Spirl MCP chain that RDL uses.

**Ordering:** In your paper workflow TAL is **after** RDL (real benchmark first, then source-traceable ADR track). That is not a hard dependency: if RDL is already done and you will not rerun it, **“Run TAL” still means only TAL**—no RDL import, no `real-data-lab/` phase scripts, no headline metric refresh unless you explicitly ask for RDL again.

## Layout

| Path | Role |
|------|------|
| `research_prompt/` | Human/agent instructions and log-location notes |
| `research/` | Checkpoints, execution log, phase reports, `trusted_adr/` JSONL |
| `research/archive/` | Timestamped copies of `research/` before big reruns |

## Run (materialize corpus + row sets)

From `Beyond Temporal Contradiction/scripts/` (path is **relative to your shell cwd**):

```powershell
python experiment_d_trusted_adr_track.py --lab-root ../trusted-adr-lab
```

From `Beyond Temporal Contradiction/`:

```powershell
python scripts/experiment_d_trusted_adr_track.py --lab-root trusted-adr-lab
```

Or use the bundled driver:

```powershell
.\run_trusted_adr_lab_e2e.ps1
```

Default (no `--lab-root`) still writes to `Beyond Temporal Contradiction/research/` for backward compatibility.

## Archive before a redo

From `Beyond Temporal Contradiction/scripts/`:

```powershell
.\archive_btc_lab_research.ps1 -LabFolder trusted-adr-lab
```

## Relation to RDL

- **RDL** (`real-data-lab/`): mixed workload MCP phases 1–3 on imported SKF.
- **This lab**: offline trusted ADR row generation + paper-facing reports; separate Spirl project IDs if you later add MCP phases for this track.

See also: [`../research/experiment_d_runbook.md`](../research/experiment_d_runbook.md) and `../research_prompt/paper3_phaseD*.md`.
