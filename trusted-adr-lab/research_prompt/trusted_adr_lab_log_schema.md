# Trusted ADR Lab — where logs go

## Default (lab layout)

When you pass `--lab-root ../trusted-adr-lab` to `experiment_d_trusted_adr_track.py`, artifacts are written **relative to this lab folder**:

```
trusted-adr-lab/research/paper3_checkpoints.experiment_D.jsonl
trusted-adr-lab/research/paper3_execution_log.experiment_D.jsonl
trusted-adr-lab/research/paper3_phase{1,2,3}_report.experiment_D.md
trusted-adr-lab/research/paper3_trusted_adr_summary.md
trusted-adr-lab/research/trusted_adr/*.jsonl
trusted-adr-lab/research/trusted_adr/README.md
trusted-adr-lab/research/trusted_adr/trusted_source_links.md
```

Entry shapes follow the same conventions as Paper 3 experiment logs where applicable; see [`../../research_prompt/paper3_log_schema.md`](../../research_prompt/paper3_log_schema.md).

## Legacy path (no `--lab-root`)

If you omit `--lab-root`, the script keeps writing under:

```
Beyond Temporal Contradiction/research/...
```

## Archive

Before overwriting, copy `research/` (excluding `research/archive/`) into `research/archive/snapshot_<UTC-timestamp>/` using `scripts/archive_btc_lab_research.ps1`.
