# Latency by exit stage

Source: `real-data-lab/research/archive/wave4_target_2026-04-21_final/real_data_lab_execution_log.jsonl`

| Exit stage | n | Median | p95 | Min | Max |
| --- | ---: | ---: | ---: | ---: | ---: |
| `structural_explicit` | 61 | 24.64 s | 54.33 s | 14.03 s | 86.31 s |
| `semantic_fast_filter` | 45 | 55.30 s | 105.91 s | 37.58 s | 151.66 s |
| `semantic_llm_judge` | 69 | 23.01 s | 75.42 s | 15.38 s | 90.09 s |
| `benign_all_clear` | 5 | 77.69 s | 85.55 s | 59.53 s | 85.55 s |
| **corpus** | **180** | **33.43 s** | **80.86 s** | 14.03 s | 151.66 s |

## Notes

- `deterministic_temporal` fires when the Stage 1 temporal lane (regression cues + anchor NLI) flags the row.  This bucket reads the patched `preflight_latency_ms` when present, otherwise falls back to the semantic-trace wall clock (overestimate).
- `structural_explicit` fires when the Stage 2/3 structural proof lane returns `detected`.
- `semantic_fast_filter` fires when the semantic lane exits via an anchor / compatibility / budget-exhaustion check before calling the LLM judge.
- `semantic_llm_judge` fires when the LLM judge is invoked.  This is the expensive bucket and dominates the corpus p95.
- The corpus row is the full-log aggregate; individual bucket counts sum to it.
