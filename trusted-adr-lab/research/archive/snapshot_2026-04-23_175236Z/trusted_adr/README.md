# Trusted ADR artifacts

Standalone Experiment D artifacts generated from the local ADR corpus.

- `adr_corpus_manifest.jsonl`: source files used
- `adr_extracted_fact_manifest.jsonl`: extracted source-backed fact rows
- `trusted_conflict_rows.jsonl`: typed conflict rows
- `trusted_benign_rows.jsonl`: benign rows
- `trusted_ambiguity_rows.jsonl`: `needs_review` pressure rows
- `trusted_manual_audit_sample.jsonl`: deterministic audit sample

These files stay separate from the live mixed RDL benchmark.
