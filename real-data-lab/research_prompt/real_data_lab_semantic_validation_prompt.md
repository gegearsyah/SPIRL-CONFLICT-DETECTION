# Semantic validation track — Real Data Lab

Use this **before** the full 110-row Phase 2 run when the priority is **semantic contradiction** (staged retrieval + NLI / cross-encoder, or your architecture’s semantic path).

## Goal

1. **Recall on true semantic contradictions:** 40 gold rows (`c-sem-01` … `c-sem-40`) should tend to produce an alert (inline detection or async notification after poll).
2. **Precision / FP control:** benign, documentation-consistent proposals should **not** alert (paraphrase and “same story” wording on overlapping baseline facts).

## Corpus (authoritative files)

| Role | File |
|------|------|
| Positive (should alert) | `real-data-lab/list_conflict_semantic_only.md` (slice of `list_conflict.md`) |
| Negative (should not alert) | `real-data-lab/list_benign_semantic_focus.md` (regenerate: `scripts/build_semantic_validation_corpus.py --write`) |

Benign rows use IDs `sb-*` and keys `p-sben-*` so they do **not** collide with a previous full `list_benign.md` run on the same project.

## Spirl project and Phase 1

- Same as the main track: one project id from **`.spirl/config.json`** (`real_data_lab_project_id` / `projects.real_data_lab_project_core_platform`).
- **Phase 1 must be complete** (`real_data_lab_checkpoints.jsonl` — baseline graph + edges).

**Recommended:** run this track on a project that has **not** already received full Phase 2 `p-*` / `p-ben-*` injections, or accept that some proposed keys from `list_conflict_semantic_only.md` may overlap prior runs.

## MCP (same as Paper 3 / Real Data Lab)

- **MCP only**, Streamable HTTP (see `research_prompt/real_data_lab_phase2_prompt.md`).
- After each scored upsert, use **preflight-primary semantic scoring**: terminal semantic preflight miss → **0s** async poll, semantic preflight hit → **15s** short poll, missing/errored semantic preflight → fallback to the full `--poll-max-wait` budget (default **90s**).
- Ground truth research facts for this track: **`research.rdl.semantic_gt.*`** (not `research.rdl.groundtruth.*`).

## Automation (preferred)

From `Beyond Temporal Contradiction/scripts/`:

```bash
python real_data_lab_semantic_conflict_mcp_run.py
python real_data_lab_semantic_benign_mcp_run.py
```

### Reuse for multiple experiments (e.g. Hoyer 0.10, 0.15, 0.25)

**Lab default:** λ = **0.25** on Spirl; **avoid 0.20** (historically bad in this setup). Tag runs with matching `--hoyer`.

Each run can have a stable **`experiment_id`** so logs and reports do not overwrite each other.

| CLI | Effect |
|-----|--------|
| `--hoyer 0.15` | Sets `hoyer_lambda` in every JSONL line’s `experiment` object and uses default id **`hoyer_0p15`** (two decimal places) → **suffixed** filenames (see below). |
| `--experiment-id my_ablation` | Forces that id (sanitized for the filesystem). Use the **same** id for conflict + benign on one backend configuration. |

**Spirl server:** apply the actual Hoyer coefficient (or other semantic-path hyperparameter) on the backend **before** each run. The scripts only record the value you pass with `--hoyer` for provenance.

**Same project, multiple λ:** proposed fact keys (`p-api-01`, `p-sben-01`, …) are reused across experiments. Prefer a **fresh Spirl project per λ**, or delete prior injected facts between runs, to avoid upsert collisions.

**Sweep helper** (runs conflict then benign for each λ, default **three** values: 0.10, 0.15, 0.25):

```bash
python real_data_lab_semantic_hoyer_sweep.py
python real_data_lab_semantic_hoyer_sweep.py --dry-run
python real_data_lab_semantic_hoyer_sweep.py --hoyers 0.25
```

Optional:

- `python real_data_lab_semantic_conflict_mcp_run.py --injection-limit 5` — smoke test.
- `python real_data_lab_semantic_conflict_mcp_run.py --poll-max-wait 120`

## Artifacts (separate from full Phase 2)

**Default** (no `--hoyer` / no `real_data_lab_semantic_experiment.id`):

| File | Purpose |
|------|---------|
| `real-data-lab/research/real_data_lab_semantic_execution_log.jsonl` | Injections + metrics (phases **4** = semantic conflicts, **5** = benign) |
| `real-data-lab/research/real_data_lab_semantic_checkpoints.jsonl` | Track boundaries / resume |
| `real-data-lab/research/real_data_lab_semantic_conflict_report.md` | Post conflict batch |
| `real-data-lab/research/real_data_lab_semantic_validation_report.md` | Pooled TP/FN/FP/TN, precision, recall |

**Named experiment** (e.g. `--hoyer 0.15` → id `hoyer_0p15`): same basenames with **`.hoyer_0p15`** before the extension, e.g. `real_data_lab_semantic_execution_log.hoyer_0p15.jsonl`.

Every log line includes `"experiment": { "id": "…", "hoyer_lambda": … }` when applicable.

## Log interpretation

**Injection-level “detected”** (same rule as mixed workload):

Semantic rows score **`result.semantic_primary_detected` first** when present. Async notification remains a transport metric, and inline detection is only fallback when semantic trace is unavailable. Legacy rows without `semantic_primary_detected` continue to use the older inline/async/notification rule.

**Phase numbers:** `4` = semantic contradiction injections; `5` = semantic benign. Do not confuse with full-track Phase 2 in `real_data_lab_execution_log.jsonl`.

## Optional `.spirl/config.json` overrides

| Key | Effect |
|-----|--------|
| `real_data_lab_semantic_conflict_list_path` | Path relative to `Beyond Temporal Contradiction/` for an alternate semantic conflict table |
| `real_data_lab_semantic_benign_list_path` | Alternate benign focus table |
| `real_data_lab_semantic_injection_limit` | Positive int: cap semantic conflict rows |
| `real_data_lab_semantic_experiment` | Object: optional `"id"` (string) and extra keys (e.g. `"hoyer_lambda"`) merged into JSONL `experiment` and path resolution |
| `real_data_lab_semantic_hoyer_lambda` | Float: default Hoyer tag + default experiment id if CLI omits `--hoyer` |

## After semantic validation passes

Proceed to full **`list_conflict.md`** Phase 2 (`real_data_lab_phase2_mcp_run.py`) and optional mixed benign (`real_data_lab_benign_mcp_run.py`) when you need dependency / constraint / temporal / ambiguous coverage.

## Semantic trace requirement

For this validation track, every scored row should request `include_semantic_trace: true` plus `expected_anchor_keys=based_on_facts` via `memory_check_conflicts_v1` before the upsert. The JSONL entry for each row should include:

- `semantic_trace_present`
- `winning_stop_reason`
- `stage_counts`
- `semantic_trace` (full backend payload when available)
- `semantic_trace_missing` when absent

This is the primary artifact for answering why a semantic contradiction was not counted even when `SPARSECL_EVERIFY_ENABLED=false`.

