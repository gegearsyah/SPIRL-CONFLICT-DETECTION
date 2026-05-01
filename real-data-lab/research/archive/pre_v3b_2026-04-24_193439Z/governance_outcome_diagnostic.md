# Governance outcome diagnostic (Wave 4.3++b preparation)

- Source: `c:\Users\GEYE ARDIANSYAH\Downloads\Innovation Hub\SPIRAL-RESEARCH\Beyond Temporal Contradiction\real-data-lab\research\real_data_lab_execution_log.jsonl`
- Rows analysed: **180**

## Outcome distribution

| outcome | n |
| --- | ---: |
| `typed_conflict` | 1 |
| `needs_review` | 120 |
| `benign` | 59 |
| `unset` | 0 |

## LLR distribution (all rows)

| bucket | n |
| --- | ---: |
| `ge_threshold(0.35)` | 1 |
| `0_to_threshold` | 0 |
| `neg_small_(-5,0)` | 2 |
| `neg_mid_(-15,-5)` | 26 |
| `neg_large_(<-15)` | 151 |

_With four lane features clamped at `eps=1e-3`, each absent lane contributes roughly `w * log(0.001/0.999) ≈ -6.9 * w` to the LLR. A single-lane hit therefore scores around -25 before `committee_agreement` / `anchor_alignment` rescue it._

## Branch histogram (all rows, mirrors `_compute_governance_outcome`)

| branch | n | description |
| --- | ---: | --- |
| `B0_deterministic_commit` | 0 | deterministic temporal hit commits typed |
| `B1_typed_commit_clean` | 0 | has_typed AND llr>=threshold AND no ambiguity |
| `B2_typed_deferred_by_ambiguity_AND_low_llr` | 27 | has_typed AND ambiguity AND llr<threshold |
| `B3_no_typed_but_ambiguity_signals` | 13 | no typed hit but ambiguity signals |
| `B4_no_typed_no_ambiguity_falls_through_aggregate` | 59 | aggregate-vs-floor gate (needs_review OR benign) |
| `B5_else_typed_gated_by_llr_only` | 81 | else branch (typed iff llr>=threshold) |

## Bucket A: typed-conflict rows routed to `needs_review` (98 rows)

Branch breakdown:

| branch | n |
| --- | ---: |
| `B5_else_typed_gated_by_llr_only` | 71 |
| `B2_typed_deferred_by_ambiguity_AND_low_llr` | 25 |
| `B3_no_typed_but_ambiguity_signals` | 2 |

Ambiguity-signal breakdown (empty list => `<none>`):

| signal | n |
| --- | ---: |
| `<none>` | 71 |
| `structural_disagreement` | 15 |
| `voronoi_ambiguous` | 12 |
| `weak_anchor_suppressed_high_conf` | 4 |
| `stage5_judge_budget_exhausted` | 1 |
| `judge_budget_exhausted` | 1 |
| `semantic_abstain:judge_budget_exhausted` | 1 |

Active-lane histogram (count of c_* > 0):

| active_lanes | n |
| --- | ---: |
| 0 | 2 |
| 1 | 71 |
| 2 | 23 |
| 3 | 2 |

First 10 typed-deferred rows (feature vector + LLR):

| row | expected | primary | LLR | branch | ambig | features |
| --- | --- | --- | ---: | --- | --- | --- |
| `c-sem-01` | `semantic_contradiction` | `semantic` | -20.94 | `B5_else_typed_gated_by_llr_only` | - | c_temporal=0.000, c_constraint=0.000, c_dependency=0.000, c_semantic=0.900, c_semantic_suppressed=0.000, committee_agreement=1.000, anchor_alignment=0.200, structural_disagreement=0.000 |
| `c-sem-02` | `semantic_contradiction` | `semantic` | -20.20 | `B5_else_typed_gated_by_llr_only` | - | c_temporal=0.000, c_constraint=0.000, c_dependency=0.000, c_semantic=0.950, c_semantic_suppressed=0.000, committee_agreement=1.000, anchor_alignment=0.200, structural_disagreement=0.000 |
| `c-sem-03` | `semantic_contradiction` | `semantic` | -20.20 | `B5_else_typed_gated_by_llr_only` | - | c_temporal=0.000, c_constraint=0.000, c_dependency=0.000, c_semantic=0.950, c_semantic_suppressed=0.000, committee_agreement=1.000, anchor_alignment=0.200, structural_disagreement=0.000 |
| `c-sem-04` | `semantic_contradiction` | `semantic` | -20.20 | `B5_else_typed_gated_by_llr_only` | - | c_temporal=0.000, c_constraint=0.000, c_dependency=0.000, c_semantic=0.950, c_semantic_suppressed=0.000, committee_agreement=1.000, anchor_alignment=0.200, structural_disagreement=0.000 |
| `c-sem-05` | `semantic_contradiction` | `semantic` | -20.20 | `B5_else_typed_gated_by_llr_only` | - | c_temporal=0.000, c_constraint=0.000, c_dependency=0.000, c_semantic=0.950, c_semantic_suppressed=0.000, committee_agreement=1.000, anchor_alignment=0.200, structural_disagreement=0.000 |
| `c-sem-06` | `semantic_contradiction` | `structural` | -18.23 | `B5_else_typed_gated_by_llr_only` | - | c_temporal=0.000, c_constraint=0.880, c_dependency=0.000, c_semantic=0.000, c_semantic_suppressed=0.000, committee_agreement=1.000, anchor_alignment=0.500, structural_disagreement=0.000 |
| `c-sem-07` | `semantic_contradiction` | `semantic` | -20.94 | `B5_else_typed_gated_by_llr_only` | - | c_temporal=0.000, c_constraint=0.000, c_dependency=0.000, c_semantic=0.900, c_semantic_suppressed=0.000, committee_agreement=1.000, anchor_alignment=0.200, structural_disagreement=0.000 |
| `c-sem-08` | `semantic_contradiction` | `semantic` | -20.20 | `B5_else_typed_gated_by_llr_only` | - | c_temporal=0.000, c_constraint=0.000, c_dependency=0.000, c_semantic=0.950, c_semantic_suppressed=0.000, committee_agreement=1.000, anchor_alignment=0.200, structural_disagreement=0.000 |
| `c-sem-09` | `semantic_contradiction` | `semantic` | -20.94 | `B5_else_typed_gated_by_llr_only` | - | c_temporal=0.000, c_constraint=0.000, c_dependency=0.000, c_semantic=0.900, c_semantic_suppressed=0.000, committee_agreement=1.000, anchor_alignment=0.200, structural_disagreement=0.000 |
| `c-sem-10` | `semantic_contradiction` | `structural` | -9.59 | `B2_typed_deferred_by_ambiguity_AND_low_llr` | structural_disagreement,voronoi_ambiguous | c_temporal=0.000, c_constraint=0.000, c_dependency=0.960, c_semantic=0.950, c_semantic_suppressed=0.000, committee_agreement=1.000, anchor_alignment=0.200, structural_disagreement=1.000 |

## Bucket B: benign rows NOT routed to `benign` (13 rows)

| outcome | n |
| --- | ---: |
| `needs_review` | 13 |

Benign row detail (full list):

| row | expected | outcome | primary | LLR | branch | ambig | features |
| --- | --- | --- | --- | ---: | --- | --- | --- |
| `b-par-03` | `benign` | `needs_review` | `governance_selector` | -28.62 | `B3_no_typed_but_ambiguity_signals` | weak_anchor_suppressed_high_conf | c_temporal=0.000, c_constraint=0.000, c_dependency=0.000, c_semantic=0.000, c_semantic_suppressed=0.900, committee_agreement=1.000, anchor_alignment=0.900, structural_disagreement=0.000 |
| `b-con-02` | `benign` | `needs_review` | `governance_selector` | -28.62 | `B3_no_typed_but_ambiguity_signals` | weak_anchor_suppressed_high_conf | c_temporal=0.000, c_constraint=0.000, c_dependency=0.000, c_semantic=0.000, c_semantic_suppressed=0.900, committee_agreement=1.000, anchor_alignment=0.900, structural_disagreement=0.000 |
| `b-mig-01` | `benign` | `needs_review` | `governance_selector` | -28.62 | `B3_no_typed_but_ambiguity_signals` | weak_anchor_suppressed_high_conf | c_temporal=0.000, c_constraint=0.000, c_dependency=0.000, c_semantic=0.000, c_semantic_suppressed=0.900, committee_agreement=1.000, anchor_alignment=0.900, structural_disagreement=0.000 |
| `b-dep-01` | `benign` | `needs_review` | `governance_selector` | -28.62 | `B3_no_typed_but_ambiguity_signals` | weak_anchor_suppressed_high_conf | c_temporal=0.000, c_constraint=0.000, c_dependency=0.000, c_semantic=0.000, c_semantic_suppressed=0.900, committee_agreement=1.000, anchor_alignment=0.900, structural_disagreement=0.000 |
| `b-nmiss-03` | `benign` | `needs_review` | `governance_selector` | -28.62 | `B3_no_typed_but_ambiguity_signals` | weak_anchor_suppressed_high_conf | c_temporal=0.000, c_constraint=0.000, c_dependency=0.000, c_semantic=0.000, c_semantic_suppressed=0.900, committee_agreement=1.000, anchor_alignment=0.900, structural_disagreement=0.000 |
| `b-nmiss-07` | `benign` | `needs_review` | `structural` | -18.81 | `B2_typed_deferred_by_ambiguity_AND_low_llr` | weak_anchor_suppressed_high_conf | c_temporal=0.000, c_constraint=0.000, c_dependency=0.780, c_semantic=0.000, c_semantic_suppressed=0.900, committee_agreement=1.000, anchor_alignment=0.900, structural_disagreement=0.000 |
| `b-nmiss-10` | `benign` | `needs_review` | `governance_selector` | -28.62 | `B3_no_typed_but_ambiguity_signals` | weak_anchor_suppressed_high_conf | c_temporal=0.000, c_constraint=0.000, c_dependency=0.000, c_semantic=0.000, c_semantic_suppressed=0.900, committee_agreement=1.000, anchor_alignment=0.900, structural_disagreement=0.000 |
| `b-comp-02` | `benign` | `needs_review` | `governance_selector` | -28.62 | `B3_no_typed_but_ambiguity_signals` | weak_anchor_suppressed_high_conf | c_temporal=0.000, c_constraint=0.000, c_dependency=0.000, c_semantic=0.000, c_semantic_suppressed=0.900, committee_agreement=1.000, anchor_alignment=0.900, structural_disagreement=0.000 |
| `b-comp-07` | `benign` | `needs_review` | `governance_selector` | -28.62 | `B3_no_typed_but_ambiguity_signals` | weak_anchor_suppressed_high_conf | c_temporal=0.000, c_constraint=0.000, c_dependency=0.000, c_semantic=0.000, c_semantic_suppressed=0.900, committee_agreement=1.000, anchor_alignment=0.900, structural_disagreement=0.000 |
| `b-comp-09` | `benign` | `needs_review` | `semantic` | -20.94 | `B5_else_typed_gated_by_llr_only` | - | c_temporal=0.000, c_constraint=0.000, c_dependency=0.000, c_semantic=0.900, c_semantic_suppressed=0.000, committee_agreement=1.000, anchor_alignment=0.200, structural_disagreement=0.000 |
| `b-ref-01` | `benign` | `needs_review` | `governance_selector` | -28.62 | `B3_no_typed_but_ambiguity_signals` | weak_anchor_suppressed_high_conf | c_temporal=0.000, c_constraint=0.000, c_dependency=0.000, c_semantic=0.000, c_semantic_suppressed=0.900, committee_agreement=1.000, anchor_alignment=0.900, structural_disagreement=0.000 |
| `b-neg-02` | `benign` | `needs_review` | `governance_selector` | -28.62 | `B3_no_typed_but_ambiguity_signals` | weak_anchor_suppressed_high_conf | c_temporal=0.000, c_constraint=0.000, c_dependency=0.000, c_semantic=0.000, c_semantic_suppressed=0.900, committee_agreement=1.000, anchor_alignment=0.900, structural_disagreement=0.000 |
| `b-neg-03` | `benign` | `needs_review` | `governance_selector` | -28.62 | `B3_no_typed_but_ambiguity_signals` | weak_anchor_suppressed_high_conf | c_temporal=0.000, c_constraint=0.000, c_dependency=0.000, c_semantic=0.000, c_semantic_suppressed=0.900, committee_agreement=1.000, anchor_alignment=0.900, structural_disagreement=0.000 |

## Bucket C: ambiguous rows (10 rows)

| outcome | n |
| --- | ---: |
| `needs_review` | 9 |
| `benign` | 1 |

## Diagnosis

- Bucket A (typed-conflict -> needs_review) dominant branch: **`B5_else_typed_gated_by_llr_only`** (71 rows).
- Rows with LLR at or above threshold (0.35): **1 / 180**.

=> Root cause is **LLR formula only** (absent-lane penalty crushes single-lane hits below threshold).  Ambiguity signals are mostly empty, so scoping them buys little; the correct knob is a **null-lane-safe LLR** (Wave D.2 new knob 5).

## Notes

- `has_typed_conflict` is reconstructed from `final_conflict_type` + `winning_detector_plane`; the shipped selector reads it from the kept-conflicts list, which the log does not record verbatim.  Both definitions agree whenever preflight authority is nested, which is the 180/180 case here.
- Branch labels mirror the if/elif ladder at `backend/app/services/cascade_router.py::_compute_governance_outcome`.
- This file is regenerated by `python scripts/governance_outcome_diagnostic.py`; do not edit by hand.
