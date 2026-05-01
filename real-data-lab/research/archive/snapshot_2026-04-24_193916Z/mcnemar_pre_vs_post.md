# Paired McNemar — Wave 4.3+ vs Wave 4.3++

- pre  log: `c:\Users\GEYE ARDIANSYAH\Downloads\Innovation Hub\SPIRAL-RESEARCH\Beyond Temporal Contradiction\real-data-lab\research\archive\pre_calibration_v3_2026-04-24_072015Z\real_data_lab_execution_log.jsonl` (180 rows)
- post log: `c:\Users\GEYE ARDIANSYAH\Downloads\Innovation Hub\SPIRAL-RESEARCH\Beyond Temporal Contradiction\real-data-lab\research\real_data_lab_execution_log.jsonl` (9 rows)
- paired rows: 9

The exact-binomial McNemar test (Edwards 1948) uses the two discordant cells
(b = pre hit, post miss; c = pre miss, post hit) under $H_0: b = c$.  A two-sided
p-value is reported so reviewers can tell which per-type deltas are within noise.

### McNemar — paired pre-vs-post (exact-type recall)

| Type | N | pre | post | Δ | b (pre-only) | c (post-only) | p (Edwards 1948) |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| semantic_contradiction | 9 | 0.889 | 0.889 | +0.000 | 0 | 0 | 1.0 |

### McNemar — paired pre-vs-post (binary detection)

| Type | N | pre | post | Δ | b (pre-only) | c (post-only) | p (Edwards 1948) |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| semantic_contradiction | 9 | 1.000 | 1.000 | +0.000 | 0 | 0 | 1.0 |

