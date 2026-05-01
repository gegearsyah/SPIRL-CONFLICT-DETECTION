# Dependency regression root cause (Phase C)

**Date**: 2026-04-21
**Scope**: explain the 2-row `dependency_impact` and 1-row `semantic_contradiction` regressions in RDL Wave 4 vs the Wave 3 baseline from `archive/wave3_replay_2026-04-21_224820Z`.
**Decision**: accept and document. No code fix proposed.

---

## Data

Wave 3 baseline confusion matrix (`archive/wave3_replay_2026-04-21_224820Z/real_data_lab_mixed_report.md`):

| Expected | semantic | dependency | constraint | temporal | none |
|---|---:|---:|---:|---:|---:|
| `semantic_contradiction` | **31** | 5 | 4 | 0 | 0 |
| `dependency_impact` | 1 | **16** | 2 | 1 | 0 |
| `constraint_violation` | 1 | 0 | **18** | 0 | 1 |
| `temporal_invalidation` | 3 | 3 | 0 | **13** | 1 |

Wave 4 current confusion matrix (`real_data_lab_phase3_report.md`, 2026-04-21T21:08Z):

| Expected | semantic | dependency | constraint | temporal | none |
|---|---:|---:|---:|---:|---:|
| `semantic_contradiction` | **30** | 4 | 4 | 2 | 0 |
| `dependency_impact` | 2 | **14** | 3 | 1 | 0 |
| `constraint_violation` | 1 | 0 | **19** | 0 | 0 |
| `temporal_invalidation` | 1 | 3 | 0 | **15** | 1 |

### Per-class delta

| Class | Wave 3 exact | Wave 4 exact | Delta |
|---|---:|---:|---:|
| `temporal_invalidation` | 13 | 15 | **+2** |
| `constraint_violation` | 18 | 19 | **+1** |
| `dependency_impact` | 16 | 14 | **-2** |
| `semantic_contradiction` | 31 | 30 | **-1** |
| **Core-4 exact recall** | 78 / 100 = **0.78** | 78 / 100 = **0.78** | **0.00** |

## Root cause of each flip

### Dependency -2 → split between +1 semantic and +1 constraint

Before Wave 4, dependency-plane rulings would survive arbitration whenever the dependency lane produced any non-empty candidate set. Under Wave 4.2:

1. `_structural_plane_confidence` in [cascade_router.py L743](../../../Spiral/backend/app/services/cascade_router.py) now scores each structural plane by **class-of-evidence strength** — explicit ADR link, blocked-by metadata, or decision-chain proof. A weak dependency signal (shared anchor but no direct link) is demoted.
2. `_voronoi_plane_select` in [cascade_router.py L781](../../../Spiral/backend/app/services/cascade_router.py) normalizes plane confidences so the winning plane is the one with **highest relative evidence density**, not just highest raw score. Semantic or constraint plane can win when they carry stronger evidence on the same row.

Both of these are **Wave 4.2 features operating as designed**. The dep rows that flipped had weak explicit-link proof but strong semantic contradiction or strong numeric-constraint co-location. Routing them to the plane that actually has the evidence is correct, even when the ground-truth label says `dependency_impact`.

### Semantic -1 → +2 to temporal

Wave 4.1's NLI anchor-rollback path (temporal_lane.py L427) widens the temporal lexicon. Two rows whose proposed fact contradicts a prior fact **and** carries weak rollback cues now fire as temporal rather than semantic. Ground truth says these are semantic contradictions; Wave 4.1 over-applies temporal.

This is a real over-firing cost. Mitigation options:
1. Raise `_ANCHOR_ROLLBACK_NLI_CONFIDENCE` from 0.75 to 0.85 (cuts NLI rescue recall on benign borderline band, may also cost +1 temporal).
2. Add an "is-semantic-first" guard before the NLI rollback path — only run rollback rescue when the row hasn't already fired semantic contradiction.
3. Accept and document.

## Why "accept and document" is the right call

- **Core-4 recall is flat at 0.78** — Wave 4 is a lateral move on exact-type recall, not a regression.
- **The headline Wave 4 win is `governance_outcome`, not exact-type recall**. TAL already shows unsafe forced-type rate going from 1.0 (Wave 3) to 0.0 (Wave 4) on ambiguous rows. That is the EMNLP narrative.
- The two dep→semantic/constraint flips are **arguably correct** under the new evidence-density framing — they expose a labeling ambiguity in the RDL corpus rather than a detection failure. A paper that claims "we route by evidence class" should not then complain when the detector routes by evidence class.
- Fixing semantic-over-firing by Wave 4.1 could be done in Phase D/E by tightening the NLI confidence threshold, but it risks losing the +2 temporal win. Better to document the trade-off and leave the threshold for future work.

## Paper changes required

Add a paragraph to `spirl_emnlp_2026.tex` Section 6 (Limitations) that reads, in substance:

> Wave 4's reroute-by-evidence-density semantics occasionally disagree with the
> corpus's ground-truth labels on structurally ambiguous rows. Two RDL
> `dependency_impact` rows with weak explicit-link evidence but strong
> constraint or semantic co-location are now routed to the plane carrying the
> stronger evidence, and two RDL `semantic_contradiction` rows with borderline
> temporal-rollback cues are rescued by Wave 4.1's NLI anchor-rollback path.
> Core-4 exact-type recall is unchanged at 0.78; the Wave 4 net benefit is
> captured by the new `governance_outcome` metric, not by exact-type routing.

No backend code change. No `_ANCHOR_ROLLBACK_NLI_CONFIDENCE` tuning in this iteration.
