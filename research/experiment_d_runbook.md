# Experiment D Runbook - Trusted ADR Track

## Why this is separate from RDL

Experiment D is intentionally **not** part of `real-data-lab/research/*`.

Why:

- `real-data-lab` is the live mixed benchmark backbone used for the main paper result surface.
- Experiment D answers a different question: can we build a **source-traceable ADR-backed track** with explicit provenance and review pressure?
- You explicitly asked not to combine the new ADR work into live RDL.

So the rule is:

- keep `real_data_lab_execution_log.jsonl` unchanged
- keep `real_data_lab_mixed_report.md` unchanged
- run Experiment D through its own logs, manifests, and reports

## What Experiment D is for

Use Experiment D when you want:

- public ADR-grounded evidence
- exact upstream source links
- standalone conflict / benign / ambiguity rows
- provenance coverage you can cite later in the paper

Do **not** use Experiment D when your goal is to update the mixed RDL headline metrics.

## Core files

### Script

- `scripts/experiment_d_trusted_adr_track.py`

### Outputs

- `research/trusted_adr/adr_corpus_manifest.jsonl`
- `research/trusted_adr/adr_extracted_fact_manifest.jsonl`
- `research/trusted_adr/trusted_conflict_rows.jsonl`
- `research/trusted_adr/trusted_benign_rows.jsonl`
- `research/trusted_adr/trusted_ambiguity_rows.jsonl`
- `research/trusted_adr/trusted_manual_audit_sample.jsonl`
- `research/trusted_adr/trusted_source_links.md`
- `research/paper3_phase1_report.experiment_D.md`
- `research/paper3_phase2_report.experiment_D.md`
- `research/paper3_phase3_report.experiment_D.md`
- `research/paper3_trusted_adr_summary.md`

### Optional: `trusted-adr-lab/` (same layout as RDL)

To keep Experiment D logs and prompts next to each other under a dedicated folder (mirrors `real-data-lab/research/` + `research_prompt/`):

- Run: `python scripts/experiment_d_trusted_adr_track.py --lab-root trusted-adr-lab` (from `Beyond Temporal Contradiction/`) or `scripts/run_trusted_adr_lab_e2e.ps1` from `scripts/`.
- Artifacts land under `trusted-adr-lab/research/` (and `trusted-adr-lab/research/trusted_adr/`).
- Snapshot before a redo: `scripts/archive_btc_lab_research.ps1 -LabFolder trusted-adr-lab`.

Default without `--lab-root` remains `research/` at the BTC root for backward compatibility.

## Corpus honesty note

This track uses:

- a **real public repository**
- with **real public ADR documents**
- but specifically a **public ADR example corpus**

Use this wording later in the paper:

- "source-traceable public ADR corpus"
- "standalone trusted ADR track"

Avoid this wording unless we replace the corpus later:

- "private enterprise ADR history"
- "internal production ADR archive"

## Recommended execution order

### Phase D0 - setup and scope

Read:

- `research_prompt/paper3_phaseD0_trusted_adr_setup_prompt.md`

Goal:

- confirm the corpus source
- confirm the separation contract
- choose `--scope` and `--max-files`

### Phase D1 - materialize the trusted track

Read:

- `research_prompt/paper3_phaseD1_trusted_adr_materialize_prompt.md`

Goal:

- run the materialization script
- generate manifests, rows, links, and standalone reports

### Phase D2 - audit and paper-facing interpretation

Read:

- `research_prompt/paper3_phaseD2_trusted_adr_audit_prompt.md`

Goal:

- verify provenance
- inspect ambiguity rows as review-pressure cases
- produce paper-safe wording

## Minimal command

```powershell
cd "C:\Users\GEYE ARDIANSYAH\Downloads\Innovation Hub\SPIRAL-RESEARCH\Beyond Temporal Contradiction\scripts"
python experiment_d_trusted_adr_track.py --scope en --max-files 200
```

## What to cite later

If you need the exact upstream links later, use:

- `research/trusted_adr/trusted_source_links.md`

If you need row-level provenance fields later, use:

- `research/trusted_adr/trusted_conflict_rows.jsonl`
- `research/trusted_adr/trusted_benign_rows.jsonl`
- `research/trusted_adr/trusted_ambiguity_rows.jsonl`

## One-line mental model

Experiment D is **RDL-adjacent evidence**, not **RDL replacement**.
