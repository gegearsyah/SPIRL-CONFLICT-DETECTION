# Semantic threshold mix report (precision, FP, and confusion matrix)

Generated (UTC): `2026-04-02T11:18:52Z`

## Setup

- **Embedding model (Stage-1 cosine):** `all-MiniLM-L6-v2`
- **SKF facts:** `C:/Users/GEYE ARDIANSYAH/Downloads/Innovation Hub/SPIRAL-RESEARCH/Beyond Temporal Contradiction/real-data-lab/Project Core Platform.skf.json`
- **Benign corpus:** `C:/Users/GEYE ARDIANSYAH/Downloads/Innovation Hub/SPIRAL-RESEARCH/Beyond Temporal Contradiction/real-data-lab/list_benign_semantic_focus.md` (26 rows) — gold = no alert
- **Semantic-contradiction corpus:** `C:/Users/GEYE ARDIANSYAH/Downloads/Innovation Hub/SPIRAL-RESEARCH/Beyond Temporal Contradiction/real-data-lab/list_conflict_semantic_only.md` (40 rows) — gold = alert
- **Candidate pool cosine floor:** `0.32` (pipeline threshold still applies per column)
- **SparseCL Stage 1.5:** disabled (patched off) for this run

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
| 0.600 | 0.920 | 0.300 | 0.820 | T | 19 | 21 | 3 | 23 | 86.36 | 47.50 | 88.46 | 11.54 | 52.50 | 63.64 | 61.29 |
| 0.600 | 0.880 | 0.300 | 0.820 | T | 19 | 21 | 3 | 23 | 86.36 | 47.50 | 88.46 | 11.54 | 52.50 | 63.64 | 61.29 |
| 0.550 | 0.920 | 0.300 | 0.820 | T | 20 | 20 | 7 | 19 | 74.07 | 50.00 | 73.08 | 26.92 | 50.00 | 59.09 | 59.70 |
| 0.550 | 0.880 | 0.300 | 0.820 | T | 20 | 20 | 7 | 19 | 74.07 | 50.00 | 73.08 | 26.92 | 50.00 | 59.09 | 59.70 |

## Full mix (4 combinations)

| embed_sim | nli | floor | high_sim | α | ev | TP | FN | FP | TN | Prec% | Rec% | Spec% | FPR% | FNR% | Acc% | F1% |
|----------:|----:|------:|---------:|--:|:--:|---:|---:|---:|---:|------:|-----:|------:|-----:|-----:|-----:|----:|
| 0.550 | 0.880 | 0.300 | 0.820 | 1.00 | T | 20 | 20 | 7 | 19 | 74.07 | 50.00 | 73.08 | 26.92 | 50.00 | 59.09 | 59.70 |
| 0.550 | 0.920 | 0.300 | 0.820 | 1.00 | T | 20 | 20 | 7 | 19 | 74.07 | 50.00 | 73.08 | 26.92 | 50.00 | 59.09 | 59.70 |
| 0.600 | 0.880 | 0.300 | 0.820 | 1.00 | T | 19 | 21 | 3 | 23 | 86.36 | 47.50 | 88.46 | 11.54 | 52.50 | 63.64 | 61.29 |
| 0.600 | 0.920 | 0.300 | 0.820 | 1.00 | T | 19 | 21 | 3 | 23 | 86.36 | 47.50 | 88.46 | 11.54 | 52.50 | 63.64 | 61.29 |
