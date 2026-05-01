# Spiral semantic stages (lab replica)

Self-contained copy of the **semantic contradiction** pipeline from Spiral’s backend:

1. **Stage 1** — Cosine gate: same-key dropped, `similarity >= CONFLICT_EMBEDDING_SIMILARITY_THRESHOLD`, top `limit` (you supply neighbor dicts; use `candidates_from_neighbors` from `GraphContext` or Neo4j).
2. **Stage 1.5** — SparseCL rerank + optional E-Verify (Hoyer floor + recall guard), matching Spiral `backend/app/services/sparsecl_service.py`.
3. **Calibration** — Spiral attaches `calibrated_similarity` when the backend isotonic calibrator is ready; here `calibration.py` is a **no-op** unless you extend it.
4. **Stage 1.75** — Predicate overlap: **soft** mode by default (Jaccard + optional rescue via embedding similarity / SparseCL Hoyer per **Spiral/docs/CONFLICT_DETECTION_ARCHITECTURE.md** Apr 2026). Set `NLI_PREDICATE_OVERLAP_MODE=hard` for strict Jaccard-only veto.
5. **Stage 2** — Bidirectional margin-gated NLI (`NLI_MODEL_NAME`, default DeBERTa v3 base): forward margin `NLI_CONTRADICTION_MARGIN_THRESHOLD`; when forward is strong, reverse may use `NLI_CONTRADICTION_REVERSE_MARGIN_THRESHOLD` (asymmetric). Optional `NLI_FORWARD_DOMINANT_OVERRIDE_*` for Spiral’s forward-dominant escape hatch. Falls back to `unverified_similarity` if NLI cannot load.

## Install

From `state-orchestration-lab/`:

```bash
pip install -r requirements.txt -r requirements-spiral-stages.txt
```

(`sentence-transformers` / `torch` are required for SparseCL + NLI.)

Optional **OpenAI** Stage-1 embeddings (e.g. `text-embedding-3-small`, as in Spirl):

```bash
pip install -r requirements-openai-embed.txt
```

The harness script `Beyond Temporal Contradiction/scripts/semantic_benign_threshold_sweep.py` loads this `.env` and defaults to **`openrouter`** when `OPENROUTER_API_KEY` is set, using `OPENROUTER_EMBEDDING_MODEL` (e.g. `openai/text-embedding-3-small`) against `OPENROUTER_BASE_URL` (normalized to `.../api/v1` even if you pasted a chat URL). Use `--embed-backend openai` or `sentence_transformers` to override.

## Environment

Same variable names as Spiral (optional `.env` in this folder or cwd):

| Variable | Default |
|----------|---------|
| `CONFLICT_EMBEDDING_SIMILARITY_THRESHOLD` | 0.35 |
| `CONTRADICTION_HIGH_SEVERITY_SIMILARITY` | 0.80 |
| `NLI_CONTRADICTION_CONFIDENCE_THRESHOLD` | 0.80 |
| `NLI_CONTRADICTION_MARGIN_THRESHOLD` | 0.40 |
| `NLI_CONTRADICTION_REVERSE_MARGIN_THRESHOLD` | 0.25 (set `0` to disable asymmetric reverse relax) |
| `NLI_FORWARD_STRONG_CONFIDENCE` | 0.95 |
| `NLI_FORWARD_STRONG_MARGIN` | 0.60 |
| `NLI_BIDIRECTIONAL_ENABLED` | true |
| `NLI_FORWARD_DOMINANT_OVERRIDE_ENABLED` | false |
| `NLI_FORWARD_DOMINANT_MIN_CONFIDENCE` | 0.97 |
| `NLI_FORWARD_DOMINANT_MIN_MARGIN` | 0.80 |
| `NLI_PREDICATE_OVERLAP_THRESHOLD` | 0.15 (set `0` to disable) |
| `NLI_PREDICATE_OVERLAP_MODE` | soft |
| `SEMANTIC_OVERLAP_NO_RESCUE_FLOOR` | 0.08 |
| `NLI_PREDICATE_OVERLAP_RESCUE_SIMILARITY` | 0.90 |
| `NLI_PREDICATE_OVERLAP_RESCUE_HOYER` | 0.30 |
| `NLI_MODEL_NAME` | cross-encoder/nli-deberta-v3-base |
| `SPARSECL_MODEL` | SparseCL/BGE-SparseCL-arguana |
| `SPARSECL_ALPHA` | 1.0 |
| `SPARSITY_ENTAILMENT_FLOOR` | 0.32 |
| `SPARSECL_EVERIFY_ENABLED` | false |

## Usage

```python
from spiral_semantic_stages import (
    candidates_from_neighbors,
    check_semantic_contradictions_stages,
    get_settings,
)
from kg_orchestrator.models import FactProposal, GraphContext

# After you load ctx: GraphContext with neighbor_facts + embeddings
proposal = FactProposal(key="k.new", body="We use TLS 1.3 everywhere.", embedding=emb)
cands = candidates_from_neighbors(
    proposal,
    ctx.neighbor_facts,
    similarity_threshold=get_settings().conflict_embedding_similarity_threshold,
    limit=10,
)
conflicts = check_semantic_contradictions_stages(
    proposal.key,
    proposal.body,
    cands,
    limit=10,
)
```

**Optional trace** (per-row forensics: Stage-1 neighbors, SparseCL meta including recall-guard, NLI softmax triples per neighbor):

```python
trace: dict = {}
check_semantic_contradictions_stages(
    proposal.key,
    proposal.body,
    cands,
    limit=10,
    trace=trace,
)
# trace["sparsecl"], trace["stage15_neighbors"], trace["nli_evaluations"], trace["hits"]
```

Return shape matches Spiral conflict dicts: `conflict_type`, `severity`, `summary`, `details`, `conflicting_fact_id`.

## Parity notes

- **Spec**: Behavior and defaults follow **Spiral/docs/CONFLICT_DETECTION_ARCHITECTURE.md** (Apr 2026): soft predicate overlap, asymmetric reverse NLI margin when forward is strong, SparseCL rerank with E-Verify **off** by default, Hoyer floor 0.32 when E-Verify is enabled. Graph enrichment (`dependency_impact` relabeling, etc.) is **post-semantic** in Spiral only; this lab package emits `semantic_contradiction` only.
- **Retrieval**: Spiral runs Neo4j/pgvector internally; this package expects **you** to pass Stage-1 candidates (or use `candidates_from_neighbors`).
- **Isotonic calibration**: not fitted in-lab by default; Spiral may add `calibrated_similarity` in production.
- **SparseCL ablation**: To match production behavior, evaluate with Stage 1.5 **on** (rerank + optional E-Verify). The sweep script can run `--ablation-sparsecl` (no 1.5 vs rerank-only vs E-Verify) in one report.
- **Paper engine**: `kg_orchestrator/engines/semantic.py` remains the Paper §3.2 baseline; this folder is **only** for Spiral-aligned research.
