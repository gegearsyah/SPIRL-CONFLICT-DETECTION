# Wave 4 constants provenance audit

**Audit date:** 2026-04-21
**Audited by:** critique response plan R12 gate
**Purpose:** document how every Wave 4 threshold was chosen so the EMNLP paper can disclose leakage risk honestly in its Limitations section. This is a gate before the R4 RDL replay.

## Scope

Every hardcoded numeric constant introduced by Wave 4.1 / 4.2 / 4.3 that materially affects a detection or arbitration decision. Deliberately excludes enum strings, regex patterns, and logging-only constants.

## Summary

| Constant | Value | File | Leakage risk | Action |
|---|---|---|---|---|
| `governance_llr_threshold` | 0.35 | [config.py](../../../../Spiral/backend/app/core/config.py):376 / [cascade_router.py](../../../../Spiral/backend/app/services/cascade_router.py):64 | **HIGH** | Disclose in paper §Limitations + architecture doc |
| `governance_ambiguous_floor` | 0.15 | [config.py](../../../../Spiral/backend/app/core/config.py):377 / [cascade_router.py](../../../../Spiral/backend/app/services/cascade_router.py):65 | **HIGH** | Disclose in paper §Limitations + architecture doc |
| `_CONSTRAINT_COLOCATION_WINDOW_TOKENS` | 8 | [constraint_lane.py](../../../../Spiral/backend/app/services/constraint_lane.py):59 | MEDIUM | Disclose guard-motivation, value is hand-picked |
| `_ANCHOR_ROLLBACK_NLI_CONFIDENCE` | 0.75 | [temporal_lane.py](../../../../Spiral/backend/app/services/temporal_lane.py):404 | LOW | Literature-standard; cite WANLI/ANLI convention |
| `_ANCHOR_ROLLBACK_MIN_CUE_SCORE` | 1.0 | [temporal_lane.py](../../../../Spiral/backend/app/services/temporal_lane.py):405 | LOW | Derived from `_REGRESSION_CUES` weights |
| `_VORONOI_TEMPERATURE` | 0.50 | [cascade_router.py](../../../../Spiral/backend/app/services/cascade_router.py):721 | LOW | Chen (2026, arXiv:2603.18174) theorem on temperature-scaled softmax; low τ preferred |
| `_VORONOI_WINNER_THRESHOLD` | 0.60 | [cascade_router.py](../../../../Spiral/backend/app/services/cascade_router.py):722 | LOW | Chen (2026) Theorem 2: θ > 1/k (k=2 floor 0.5) + 0.10 margin |
| `_VORONOI_MIN_MARGIN` | 0.10 | [cascade_router.py](../../../../Spiral/backend/app/services/cascade_router.py):723 | LOW | Conservative hand-picked default |
| `_SEVERITY_TO_CONFIDENCE` table | critical=0.95 ... info=0.40 | [cascade_router.py](../../../../Spiral/backend/app/services/cascade_router.py):725 | LOW | Convention-standard monotone mapping |
| `_PROOF_STRENGTH_BOOST` table | ±0.15 max | [cascade_router.py](../../../../Spiral/backend/app/services/cascade_router.py):734 | LOW | Hand-picked small calibration deltas |

## Detailed provenance

### HIGH leakage: governance thresholds

#### `governance_llr_threshold = 0.35` and `governance_ambiguous_floor = 0.15`

**Source comments in code** ([cascade_router.py](../../../../Spiral/backend/app/services/cascade_router.py) lines 60-65):

```
# Wave 4.3 Neyman-Pearson LLR selector.  Thresholds calibrated offline
# against the 10 RDL ambiguous rows + 4 TAL ambiguity rows using the
# El-Yaniv & Wiener's selective classification frame; the defaults here
# are the frozen values from the 10 RDL ambiguous + 4 TAL ambiguity
# calibration set.  Override via settings for ablation runs.
_GOV_LLR_THRESHOLD: float = 0.35
_GOV_AMBIG_FLOOR: float = 0.15
```

And in [config.py](../../../../Spiral/backend/app/core/config.py) lines 372-377:

```
# Defaults are the frozen values calibrated on the 10 RDL ambiguous
# rows + 4 TAL ambiguity rows.
governance_llr_threshold: float = 0.35
governance_ambiguous_floor: float = 0.15
```

**How the calibration was done.** The 14 rows (10 RDL + 4 TAL marked ambiguous) were passed through the cascade with `governance_outcome_enabled=True`. The LLR distribution was examined; the threshold was picked so the `needs_review` set matched the human-labelled ambiguous set. The `ambiguous_floor` was picked so benign rows (confidence below floor) would not be routed to `needs_review`.

**Why this is leakage risk.** The paper reports `needs_review` rate and `unsafe_forced_type_rate` on the full 180 RDL + 18 TAL evaluation. The 14 rows used to calibrate the thresholds are a strict subset of those evaluation rows. Strictly speaking, any row that was in the calibration set cannot also be a clean evaluation row for the threshold's discriminative power.

**Magnitude.** 14 calibration rows / 198 total = ~7% overlap. The headline ambiguous-routing claims are dominated by the 184 other rows, but the claim "`unsafe_forced_type_rate = 0%` on TAL" specifically benefits from seeing the 4 TAL ambiguity rows during calibration.

**Disclosure plan.** Paper §Limitations will say:

> The governance thresholds (`governance_llr_threshold = 0.35`, `governance_ambiguous_floor = 0.15`) were hand-calibrated on 14 human-labelled ambiguous rows (10 RDL, 4 TAL) and then held fixed for the evaluation reported in Tables 2 and 3. The calibration set is a subset of the evaluation set; strictly, 4 of the 18 TAL rows and 10 of the 180 RDL rows therefore do not contribute to out-of-sample evidence for the specific threshold values. The thresholds were not swept on the full corpus. We plan a future iteration with a held-out ambiguity set drawn from a third corpus to remove this overlap.

**Refit decision.** Not refitting for this submission. Refitting requires new ambiguous rows that we do not currently have, and the cleaner experiment (threshold swept on a held-out 15-row ambiguity set) is better deferred to a future paper than rushed into the current submission.

### MEDIUM leakage: constraint co-location guard

#### `_CONSTRAINT_COLOCATION_WINDOW_TOKENS = 8`

**Source comment in code** ([constraint_lane.py](../../../../Spiral/backend/app/services/constraint_lane.py) lines 29-36):

```
# Wave 4.2: constraint-vocabulary families used by the numeric co-location
# guard.  Each constraint_type has a set of cue words that MUST appear
# within ``_CONSTRAINT_COLOCATION_WINDOW_TOKENS`` of the numeric span for
# a structured violation to fire.  Addresses 4/40 semantic-to-constraint
# over-routes where the fact body happened to contain a number adjacent
# to (but not describing) a metric-name in the constraint (e.g. "sprint
# velocity 14 story points" matching a "max team size = 14 engineers"
# team_size constraint).  Grounded in CONFLICTS Oracle-prompt evidence
# discrimination (Cattan et al., arXiv:2506.08500).
```

**Why MEDIUM, not HIGH.** The *mechanism* (co-location guard) was added after observing 4 false-positive over-routes on RDL. The *value* 8 tokens was not swept against RDL; it is a hand-picked span consistent with typical sentence-clause length.

**Disclosure plan.** Paper §Limitations mentions:

> The numeric co-location guard in the constraint lane was added after observing 4/40 semantic-to-constraint over-routes on the RDL Wave 3 baseline. The guard is an ablation-documented mechanism (`constraint_colocation_guard_enabled=False` reproduces the Wave 3 behavior), but its introduction was informed by RDL observations.

### LOW leakage: literature-grounded or conservative defaults

#### `_ANCHOR_ROLLBACK_NLI_CONFIDENCE = 0.75`

Standard NLI confidence convention used by WANLI (arXiv:2201.05955) and the DeBERTa-v3-mnli-fever-anli-ling-wanli card. [`wave4_dependency_regression_rootcause.md`](wave4_dependency_regression_rootcause.md) line 79 explicitly records:

> No backend code change. No `_ANCHOR_ROLLBACK_NLI_CONFIDENCE` tuning in this iteration.

so the 0.75 value was **not** swept even when a semantic regression was observed that could have been mitigated by raising it to 0.85. This is the strongest evidence for non-RDL provenance.

#### `_ANCHOR_ROLLBACK_MIN_CUE_SCORE = 1.0`

Derived from `_REGRESSION_CUES` weight table:

```
(re.compile(r"\brevert(?:s|ed|ing)?\b", re.IGNORECASE), 2.0),
...
```

Single weak-cue score is 1.0 (one `blocks` / `deprecates` / similar hit). The 1.0 floor excludes rows with zero cues while keeping rows with one weak cue. Docstring calls this "borderline band `[1.0, 1.5)`" — i.e. this is the boundary between "no cue" and "one cue", not a tuned value.

#### `_VORONOI_TEMPERATURE = 0.50`

Chen (2026, "Conflict-Free Policy Languages for Probabilistic ML Predicates", arXiv:2603.18174, §4.3) recommends low τ for decisive winners: "low τ (e.g., 0.1) is preferred to ensure a decisive winner". Our 0.50 is mid-range, trading decisiveness for softness in ambiguous cases. Chosen by inspection of Chen §4.3; no RDL sweep.

#### `_VORONOI_WINNER_THRESHOLD = 0.60`

Chen (2026) Theorem 2: under Voronoi normalization with threshold θ > 1/k, at most one signal fires. For k=2 planes this gives θ > 0.50. Adding a 0.10 margin yields 0.60 to avoid tie-adjacent decisions.

#### `_VORONOI_MIN_MARGIN = 0.10`

Hand-picked conservative default. Any pair where p_struct and p_sem are within 10 percentage points routes to `ambiguous`, preventing the arbitration from making high-confidence calls on near-tie cases. No RDL sweep.

#### `_SEVERITY_TO_CONFIDENCE` table

Convention-standard monotone mapping:

```
critical: 0.95, high: 0.90, warning: 0.80, medium: 0.75, low: 0.55, info: 0.40
```

No RDL influence; values chosen to be strictly ordered and centered on common defaults.

#### `_PROOF_STRENGTH_BOOST` table

Small adjustments (±0.15 max) applied to structural confidence based on path-proof strength enum:

```
explicit_path: +0.05, reverse_alignment: +0.03, rule_program: +0.05,
reverse_entity_hit: -0.10, shared_tokens_only: -0.15
```

Hand-picked to nudge the Voronoi inputs toward high-evidence structural conflicts. Small magnitude keeps the pure literature-derived confidence (from Chen 2026) dominant.

## What this means for the R4 replay

The R4 replay proceeds as planned. The governance thresholds remain at their 0.35 / 0.15 frozen values — we do **not** retune on the new snapshot, because doing so would produce a second-order leakage (thresholds tuned on rows that also appear in the evaluation).

The paper's §Limitations will disclose:
1. Governance thresholds calibrated on 14 rows that are a subset of the evaluation set
2. Constraint co-location guard mechanism motivated by 4 RDL-observed over-routes
3. All other Wave 4 constants are either literature-derived or hand-picked with conservative defaults

This audit is the source of truth for the R11 architecture doc update.

## Files updated as a consequence of this audit

- This document: new source of truth for Wave 4 constants provenance
- Paper [spirl_emnlp_2026.tex](../../paper/ACL%20STYLE%20-%20BEYOND%20TEMPORAL/spirl_emnlp_2026.tex) §Limitations: adds the two disclosures above (delivered via R5/R13 paper edits)
- Architecture doc [CONFLICT_DETECTION_ARCHITECTURE.md](../../../../Spiral/docs/CONFLICT_DETECTION_ARCHITECTURE.md) Wave 4 section: references this document (delivered via R11)
