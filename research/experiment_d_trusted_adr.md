# Paper 3 - experiment registry

Use this file to record what each run label means. Values in `.spirl/config.json` drive where experiment-specific logs and reports are written.

| Experiment | Purpose | Primary artifacts |
|------------|---------|-------------------|
| **A/B/C** | Synthetic and realistic curated paper experiments | `research/paper3_execution_log*.jsonl`, `research/paper3_phase2_report*.md` |
| **ADR** | Read-only observation track over the cloned ADR corpus | `research/paper3_execution_log.experiment_ADR.jsonl`, `research/paper3_adr_phase*.md` |
| **D** | Standalone trusted ADR benchmark and ADR KG helper track | `research/paper3_execution_log.experiment_D.jsonl`, `research/paper3_phase*_report.experiment_D.md`, `research/trusted_adr/*` |

## Experiment D

Experiment D stays separate from `real-data-lab/` and from the live mixed RDL benchmark.

Corpus note:

- the standalone trusted ADR track uses a **public ADR example corpus**
- this is real public data from a real repository, but it is not the same as a private enterprise-internal ADR archive
- exact upstream GitHub links are written to `research/trusted_adr/trusted_source_links.md`

Two scripts now support it:

1. `scripts/experiment_d_adr_kg_pipeline.py`
   - ADR baseline fact upserts into the dedicated ADR project
   - optional small legacy seed conflict injections

2. `scripts/experiment_d_trusted_adr_track.py`
   - standalone trusted ADR manifests
   - standalone trusted conflict / benign / ambiguity rows
   - deterministic manual-audit sample
   - standalone markdown reports

Core rule:

- do **not** merge Experiment D outputs into `real-data-lab/research/*`
- do **not** treat Experiment D rows as part of the live mixed denominator
- do **not** write trusted ADR rows into `real_data_lab_execution_log.jsonl`

Experiment D is intended to answer a different question:

- can Spirl's governance framing be backed by a separate, source-traceable ADR-based track?
