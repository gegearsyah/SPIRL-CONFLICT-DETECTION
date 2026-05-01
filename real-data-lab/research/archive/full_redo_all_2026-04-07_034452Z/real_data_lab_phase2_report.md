# Phase 2 Report — Real Data Lab (Conflict injection)

Generated: 2026-04-07T01:48:49Z

## Corpus

- Source: `real-data-lab/list_conflict.md` (resolved: `C:\Users\GEYE ARDIANSYAH\Downloads\Innovation Hub\SPIRAL-RESEARCH\Beyond Temporal Contradiction\real-data-lab\list_conflict.md`)
- Mode: table-driven
- Project: `af5ff473-812b-4b03-abe0-f8e3bf44bc7a`
- Rows attempted: **110**
- Injection limit applied: **False**

## Results by conflict_class

| conflict_class | conflict_injected (log) | injection_failed (log) |
|----------------|-------------------------:|-----------------------:|
| `semantic_contradiction` | 40 | 0 |
| `dependency_impact` | 20 | 0 |
| `constraint_violation` | 20 | 0 |
| `temporal_invalidation` | 20 | 0 |
| `ambiguous_case` | 10 | 0 |
| **TOTAL** | **110** | **0** |

## Baseline simulation

Rule: baseline only flags **same-key overlapping validity** (Paper 3). Proposed facts use **p-*** keys, so `baseline_detectable` is **0** for all five classes; `baseline_missed` matches per-class row counts for this run.

Logged: `baseline_simulation` in `real_data_lab_execution_log.jsonl`; fact `research.rdl.baseline.simulation`.

## Missing baseline keys (preflight)

None logged.

## Failed corpus_row_id (if any)

None.

---

## Scoring — conflict rows only (`c-*`, same rules as mixed workload)

Metrics below are derived from `conflict_injected` lines in the execution log. They match the **Conflicts** section of `real_data_lab_mixed_report.md` when Phase 2b has not run (no `b-*` / `sb-*` rows yet).

| Metric | Value |
|--------|------:|
| Rows scored (`c-*`) | 110 |
| Binary detected (any alert) | 54 |
| Binary recall | 0.4909 |
| Exact-type detected | 24 |
| Exact-type recall | 0.2182 |
| Cross-type alerts | 28 |
| Abstained rows | 56 |

### Per-class breakdown

| conflict_class | injected | binary_detected | exact_detected | cross_type | abstained |
|----------------|---------:|----------------:|---------------:|-----------:|----------:|
| `semantic_contradiction` | 40 | 21 | 21 | 0 | 19 |
| `dependency_impact` | 20 | 8 | 0 | 8 | 12 |
| `constraint_violation` | 20 | 9 | 1 | 8 | 11 |
| `temporal_invalidation` | 20 | 14 | 2 | 12 | 6 |
| `ambiguous_case` | 10 | 2 | 0 | 0 | 8 |

### Exact-type confusion matrix (predicted vs expected)

| Expected | semantic | dependency | constraint | temporal | none |
|----------|---------:|-----------:|-----------:|---------:|-----:|
| `semantic_contradiction` | 21 | 0 | 0 | 0 | 19 |
| `dependency_impact` | 8 | 0 | 0 | 0 | 12 |
| `constraint_violation` | 4 | 0 | 1 | 0 | 11 |
| `temporal_invalidation` | 11 | 0 | 0 | 2 | 6 |
| `ambiguous_case` | 1 | 0 | 0 | 0 | 8 |

_Detection rule: semantic rows only score as semantic when `semantic_verdict=detected`; structural rows only score exact-type when their own expected class is detected in preflight or exact-type async fallback (same note as mixed workload report)._

## Flagging & transport (aggregated from `result` on conflict rows)

_Aggregated over **110** `c-*` `conflict_injected` lines for this project._

### `detection_audit.classification`

| Bucket | Count |
|--------|------:|
| `no_inline_metrics_async_unmatched` | 56 |
| `alert_async_only` | 54 |

### `primary_detector_source`

| Bucket | Count |
|--------|------:|
| `preflight` | 100 |

### `async_observed.poll_policy`

| Bucket | Count |
|--------|------:|
| `full_async_fallback` | 72 |
| `short_detected_preflight` | 21 |
| `skip_terminal_preflight` | 17 |

### `notification.created` (true/false)

| Bucket | Count |
|--------|------:|
| `False` | 56 |
| `True` | 54 |

### `preflight_semantic.semantic_verdict`

| Bucket | Count |
|--------|------:|
| `detected` | 45 |
| `unavailable` | 38 |
| `rejected` | 16 |
| `abstain` | 1 |

### `outcome_class`

| Bucket | Count |
|--------|------:|
| `detected` | 45 |
| `unavailable` | 38 |
| `abstain` | 17 |

### `semantic_primary_source`

| Bucket | Count |
|--------|------:|
| `preflight` | 40 |

### `structural_primary_source`

| Bucket | Count |
|--------|------:|
| `preflight` | 60 |

## Phase 2b (benign) — not required for this report

No benign `b-*` / `sb-*` `conflict_injected` rows were found in the log. **Pooled precision/recall and benign FP** (mixed workload) only apply after `python real_data_lab_benign_mcp_run.py`. If present, re-run this report after 2b to refresh scoring, or open `real_data_lab_mixed_report.md`.

## Artifacts

- Execution log: `real-data-lab/research/real_data_lab_execution_log.jsonl`
- Checkpoints: `real-data-lab/research/real_data_lab_checkpoints.jsonl`
