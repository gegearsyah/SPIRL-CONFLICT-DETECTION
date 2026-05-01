# Semantic forensics run summary

Generated from local harness runs (UTC machine time). **Config held constant** across ablations except where noted: `sim=0.58`, `nli=0.94`, `floor=0.20`, `high=0.82`, `ev=true`, OpenRouter `text-embedding-3-small`, default pool floor `0.32` unless overridden.

## Metrics (26 benign + 40 semantic gold)

| Experiment | Benign FP | Semantic TP / 40 | Notes |
|------------|-----------|-------------------|--------|
| Baseline | 0 | 11 | Matches prior mix-report slice |
| Predicate gate off (`--nli-predicate-overlap 0`) | 0 | **17** | Largest recall gain, precision unchanged on this slice |
| Bidirectional off (`--no-nli-bidirectional`) | **1** | 12 | Trades benign control for small recall bump |
| Pool floor 0.25 (`--pool-sim-floor 0.25`) | 0 | 11 | No change vs baseline here |
| NLI margin 0.20 (`--nli-margin-threshold 0.20`) | 0 | 11 | No change vs baseline here |
| SparseCL stacks (`--ablation-sparsecl`) | 0 | 11 | `no_stage15`, `sparsecl_rerank_only`, `sparsecl_everify_on` all **11/40** on this grid point |

## Stage-level signal (baseline per-row trace, FN rows only)

Source: `semantic_per_row_trace.baseline.jsonl`, aggregated over **false-negative** semantic rows (29 rows).

- **12** FN rows had **empty** `trace.nli_evaluations` (no NLI line items — nothing reached NLI or no candidates in trace).
- Among rows with evaluations, dominant drop code: **`predicate_overlap_skip`** (25 evaluation lines total across those rows).
- Other gates seen: `filtered_entailment_or_neutral` (9), `below_nli_confidence_forward` (1), `filtered_bidirectional_or_margin_reverse` (1).

**Interpretation:** On this slice, **Stage 1.75 predicate overlap** is the main lever; **SparseCL / E-Verify** did not change outcomes at this single threshold point (recall guard appears active in logs: “E-Verify would drop all … falling back …”). **NLI threshold sweeps** were flat earlier because many rows never got past predicate / retrieval.

## Artifacts

| File | Content |
|------|---------|
| `semantic_per_row_trace.baseline.jsonl` | Full `trace` per corpus row (baseline settings) |
| `semantic_forensics_baseline_report.md` / `.csv` | Single-config sweep table |
| `semantic_ablation_no_predicate_gate.*` | Predicate-off metrics |
| `semantic_ablation_no_bidirectional.*` | Unidirectional NLI metrics |
| `semantic_ablation_pool_0p25.*` | Lower pool floor |
| `semantic_ablation_margin_0p20.*` | Lower margin gate |
| `semantic_ablation_sparsecl_stacks.*` | Three SparseCL modes |

## Suggested next step

Shadow or adopt **`nli_predicate_overlap_threshold=0`** (or lower Jaccard) in backend config **only after** confirming no regression on a wider benign set; this slice shows **0→1 FP** only when bidirectional was disabled, not when predicate was disabled.
