# Semantic threshold mix report (precision, FP, and confusion matrix)

Generated (UTC): `2026-04-02T22:55:43Z`

## Setup

- **Stage-1 embeddings:** `openrouter:openai/text-embedding-3-small @ https://openrouter.ai/api/v1`
- **SKF facts:** `C:/Users/GEYE ARDIANSYAH/Downloads/Innovation Hub/SPIRAL-RESEARCH/Beyond Temporal Contradiction/real-data-lab/Project Core Platform.skf.json`
- **Benign corpus:** `C:/Users/GEYE ARDIANSYAH/Downloads/Innovation Hub/SPIRAL-RESEARCH/Beyond Temporal Contradiction/real-data-lab/list_benign_semantic_focus.md` (26 rows) — gold = no alert
- **Semantic-contradiction corpus:** `C:/Users/GEYE ARDIANSYAH/Downloads/Innovation Hub/SPIRAL-RESEARCH/Beyond Temporal Contradiction/real-data-lab/list_conflict_semantic_only.md` (40 rows) — gold = alert
- **Candidate pool cosine floor:** `0.25` (pipeline threshold still applies per column)
- **Stacking:** Spiral-shaped path: SparseCL loads when available; `ev` column reflects grid (SPARSECL_EVERIFY_ENABLED).
- **Gate overrides (research harness):** pool_sim_floor=`0.25` no fixed overrides for predicate / bidirectional / margin (Spiral defaults on each row)

## Replication limits

- **Labeled rows:** 66 total — adequate for coarse threshold search; small moves in F1/precision often do not replicate. Prefer a holdout slice of the markdown tables or a second corpus before locking prod.
- **Embed space:** Cosine thresholds apply only in the same embedding model + normalization regime as production. Prefer `--embed-backend openrouter` (defaults when `OPENROUTER_API_KEY` is set) or `--embed-backend openai` to match Spirl before copying numeric gates into `.env`.
- **Per-row forensics:** Use `--per-row-jsonl` with the same stack/embedder to get neighbor lists, SparseCL meta (recall guard, Hoyer), and NLI softmax triples per evaluated neighbor.

## Definitions

| Term | Meaning |
|------|---------|
| TP | Contradiction row: pipeline emitted ≥1 semantic hit |
| FN | Contradiction row: no hit (missed) |
| FP | Benign row: pipeline emitted ≥1 hit (false alert) |
| TN | Benign row: no hit (correct silence) |
| Precision | TP / (TP + FP) |
| Recall | TP / (TP + FN) |
| Specificity | TN / (TN + FP) |
| NPV | TN / (TN + FN) |
| FPR | FP / (FP + TN) — benign false-alarm rate |
| FNR | FN / (TP + FN) — miss rate on contradictions |
| Accuracy | (TP + TN) / total |

_Percentages are 0–100. Empty cells = undefined (e.g. no positives in eval)._

## Top configs by F1 (then precision)

| embed_sim | nli | floor | high_sim | ev | TP | FN | FP | TN | Prec% | Rec% | Spec% | FPR% | FNR% | Acc% | F1% |
|----------:|----:|------:|---------:|:--:|---:|---:|---:|---:|------:|-----:|------:|-----:|-----:|-----:|----:|
| 0.580 | 0.940 | 0.200 | 0.820 | T | 11 | 29 | 0 | 26 | 100.00 | 27.50 | 100.00 | 0.00 | 72.50 | 56.06 | 43.14 |

## Full mix (1 combinations)

| embed_sim | nli | floor | high_sim | α | ev | TP | FN | FP | TN | Prec% | Rec% | Spec% | FPR% | FNR% | Acc% | F1% |
|----------:|----:|------:|---------:|--:|:--:|---:|---:|---:|---:|------:|-----:|------:|-----:|-----:|-----:|----:|
| 0.580 | 0.940 | 0.200 | 0.820 | 1.00 | T | 11 | 29 | 0 | 26 | 100.00 | 27.50 | 100.00 | 0.00 | 72.50 | 56.06 | 43.14 |
