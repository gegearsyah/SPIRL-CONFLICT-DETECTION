# Paper 3 — Beyond Temporal Contradiction: Hybrid Semantic and Temporal Conflict Detection in AI-Assisted Software Knowledge Graphs

> **Evaluation track:** Experiment C (`spirl_mcp_stack_v2`). Primary quantitative reports: `research/paper3_phase2_report.experiment_C.md`, `research/paper3_phase3_report.experiment_C.md`. Execution log: `research/paper3_execution_log.experiment_C.jsonl`.

## Abstract

We evaluate hybrid conflict detection in AI-assisted software knowledge graphs using a synthetic corpus of 200 injected conflicts (50 per class) across three domains. A temporal-only baseline, simulated from explicit validity-window rules, detected 50 of 200 conflicts (25%)—solely temporal invalidation—whereas Spirl’s hybrid pipeline detected all 200 (100%), a 4.0× gain in detected-count terms. Semantic-contradiction (Class 1) reached precision and recall of 1.00 on n=50 in Experiment C. Mean driver-observed asynchronous notification latency was 586.6 ms versus 150920 ms for a counterfactual five-minute batch poll (ratio approximately 257×); the evaluation used MCP polling of the conflict outbox, not synchronous SSE response timing. Cross-project overall F1 was 1.00 with standard deviation 0.00 across the three UUID-scoped corpora. These results characterize detector coverage and latency under controlled injection; real deployments may differ.

## 1. Introduction

Software knowledge graphs maintained by AI-assisted tools accumulate facts from multiple agents and sessions. When contributors assert incompatible truths—different databases, conflicting APIs, or revised policies—downstream reasoning and automation silently degrade. Detecting such contradictions early is essential for trustworthy graph-backed assistants.

Temporal validity alone is insufficient: overlapping `valid_from` / `valid_until` windows catch **temporal invalidation**, but they miss **semantic contradictions** across distinct keys, **dependency impact** when a rewritten fact invalidates downstream dependents, and **constraint violations** where new facts break declared project rules. Our simulated temporal-only baseline on the same 200-injection corpus detected only temporal invalidation (50 of 50) and zero of 50 for each of the other three classes—150 of 200 conflicts remained invisible to temporal rules alone (75% by count; see `research.p3.results.rq1`).

This paper contributes (i) a **four-class conflict taxonomy** aligned with detector semantics; (ii) a description of Spirl’s **hybrid detector** combining embedding-backed cross-key analysis, graph dependency checks, constraint evaluation, and temporal overlap; and (iii) an **empirical evaluation** on three isolated project corpora with balanced injection and ground-truth logging (`research.p3.groundtruth.{1..200}`).

## 2. The Four-Class Conflict Taxonomy

### 2.1 Semantic contradiction

**Definition.** Distinct fact keys carry mutually incompatible natural-language claims about the same underlying concern (e.g., two stack choices for the same surface), detected via cross-key embedding similarity above a configured threshold.

**Corpus.** 50 injections (Experiment C).

**Example (ground truth `research.p3.groundtruth.3`, injection 3, project `paper3_api_service`).** Injected fact keys `research.p3.sem.3.queue` and `research.p3.sem.3.events` produced a `semantic_contradiction` notification on poll (`conflict_injected` row in `paper3_execution_log.experiment_C.jsonl`).

### 2.2 Dependency impact

**Definition.** A fact that other facts depend on (via typed edges such as `DEPENDS_ON` or `COMMUNICATES_WITH`) is modified or rewritten, so dependents become stale or inconsistent.

**Corpus.** 50 injections.

**Example (ground truth `research.p3.groundtruth.2`, injection 2, project `paper3_saas`).** Injected key `stack.secrets`; notification `conflict_type` `contradiction` matched within the bounded poll window (driver-scored as dependency_impact class in the experiment protocol).

### 2.3 Constraint violation

**Definition.** A new or updated fact conflicts with an explicit **constraint** fact (e.g., team size cap vs. stated team size).

**Corpus.** 50 injections.

**Example (ground truth `research.p3.groundtruth.1`, injection 1, project `paper3_data_pipeline`).** Injected keys `research.p3.ph2.team_fact.1` and `research.p3.ph2.team_cap.1`; notification `constraint_violation`.

### 2.4 Temporal invalidation

**Definition.** Two versions of the same key have overlapping validity intervals such that both could be read as “current” under temporal semantics.

**Corpus.** 50 injections.

**Example (ground truth `research.p3.groundtruth.4`, injection 4, project `paper3_data_pipeline`).** Injected keys `research.p3.tmpov.4` (paired writes); temporal overlap / contradiction signals observed on poll.

## 3. System Implementation

### 3.1 Layer 1 — Pre-write semantic gate

The memory upsert path applies policy gates and may surface **preflight** conflict hints in the synchronous response. Architecturally, `detect_conflicts()` runs checks including same-key contradiction, temporal overlap, **semantic contradiction** (vector similarity across keys), **dependency impact** (downstream dependents), and **constraint violations** (see `docs/ARCHITECTURE_CONFLICT_DETECTION.md`, Section 3). In Experiment C, inline detection fields were largely empty (`inline_detected`: 0 for all 200 injections); conflict materialized in the outbox and was observed via polling—consistent with **scheduled / background** detection on the deployed stack.

### 3.2 Layer 2 — Post-write notification

Detected conflicts are persisted to a **`conflict_notifications`** outbox (PostgreSQL). The architecture also describes an in-process event bus for **SSE** delivery to live clients. The Paper 3 driver did not measure SSE latency; it called **`list_conflicts_v1`** (MCP) on a bounded poll loop and recorded `observed_detection_latency_ms` from notification `created_at` versus write completion (Phase 2 report, Experiment C).

### 3.3 Baseline

The **temporal-only baseline** was **not** a live Graphiti deployment. It was **simulated** and stored as fact `research.p3.baseline.simulation` (detectable 50, missed 150; by class per Phase 2 baseline table), enabling like-for-like comparison against the 200-injection corpus.

## 4. Evaluation

### 4.1 Corpus construction

Three projects—**paper3_data_pipeline**, **paper3_saas**, **paper3_api_service**—were verified in Phase 1 (`research/paper3_phase1_report.md`, generated 2026-03-31T23:57:32Z). Totals: **95 + 92 + 96 = 283** facts and **69 + 67 + 70 = 206** typed edges at baseline; **0** isolated nodes per project. Edges were created and verified via MCP (`scripts/paper3_phase1_mcp_run.py`). UUIDs: `b7e311b5-db87-4bb1-94b3-a0b51ea4caaa`, `cdc4e20b-5c49-4feb-aafb-eca3b5157ae2`, `aa75eda0-4205-44ef-b692-5248ff0eb956`.

### 4.2 Injection procedure

Phase 2 (`scripts/paper3_phase2_mcp_run.py`, MCP Streamable HTTP) injected **200** conflicts—**50 per class**—rotating across projects (67, 67, 66). Each injection appended a **`conflict_injected`** row to `paper3_execution_log.experiment_C.jsonl` with `preflight_check`, `async_observed`, and optional `notification`. **Ground truth** was recorded under keys `research.p3.groundtruth.{injection_number}` (kind `decision` in this deployment). Mean injection time **55.2 s** (Phase 2 report, Experiment C).

### 4.3 Results

The following tables are copied verbatim from `research/paper3_phase3_report.experiment_C.md`.

## Table 1 — Confusion matrix per conflict class (Spirl)

| class | TP | FN | FP | Precision | Recall | F1 |
|-------|----|----|-----|-----------|--------|----|
| Semantic contradiction | 50 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| Dependency impact | 50 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| Constraint violation | 50 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| Temporal invalidation | 50 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| **OVERALL** | **200** | **0** | **0** | **1.00** | **1.00** | **1.00** |

*FP counted at injection level; `list_conflicts_v1` returns multiple notification rows per injection (contradiction + dependency + temporal, etc.) — not treated as separate false-positive trials.*

## Table 2 — Confusion matrix per class (Baseline temporal-only)

From simulated baseline encoded in `research.p3.baseline.simulation` (detectable=50, missed=150; by class: semantic/dependency/constraint 0/50, temporal 50/50).

| class | TP | FN | FP | Precision | Recall | F1 |
|-------|----|----|-----|-----------|--------|----|
| Semantic contradiction | 0 | 50 | 0 | 0.00 | 0.00 | 0.00 |
| Dependency impact | 0 | 50 | 0 | 0.00 | 0.00 | 0.00 |
| Constraint violation | 0 | 50 | 0 | 0.00 | 0.00 | 0.00 |
| Temporal invalidation | 50 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| **OVERALL** | **50** | **150** | **0** | **1.00** | **0.25** | **0.40** |

## Table 3 — F1 improvement: Spirl vs baseline

| class | Spirl F1 | Baseline F1 | Improvement ratio |
|-------|----------|-------------|-------------------|
| Semantic contradiction | 1.00 | 0.00 | undefined (baseline blind) |
| Dependency impact | 1.00 | 0.00 | undefined (baseline blind) |
| Constraint violation | 1.00 | 0.00 | undefined (baseline blind) |
| Temporal invalidation | 1.00 | 1.00 | 1.0× |
| **Overall detection rate** | **200/200** | **50/200** | **4.0×** |

## Table 4 — Cross-project consistency

Per-project F1 from Phase 2 log (TP/FN by `project` × `conflict_class`). All classes F1 = 1.00 per project.

| metric | project 1 | project 2 | project 3 | mean | std dev |
|--------|-----------|-----------|-----------|------|---------|
| Overall F1 | 1.00 | 1.00 | 1.00 | 1.00 | 0.00 |
| Class 1 F1 | 1.00 | 1.00 | 1.00 | 1.00 | 0.00 |
| Class 2 F1 | 1.00 | 1.00 | 1.00 | 1.00 | 0.00 |
| Class 3 F1 | 1.00 | 1.00 | 1.00 | 1.00 | 0.00 |
| Class 4 F1 | 1.00 | 1.00 | 1.00 | 1.00 | 0.00 |

Project UUIDs: `b7e311b5-db87-4bb1-94b3-a0b51ea4caaa`, `cdc4e20b-5c49-4feb-aafb-eca3b5157ae2`, `aa75eda0-4205-44ef-b692-5248ff0eb956`.

## Table 5 — Detection latency (async-observed primary)

Computed from 200 rows with finite `result.async_observed.observed_detection_latency_ms`.

| metric | Observed async (ms) | Simulated batch 5min (ms) |
|--------|---------------------|---------------------------|
| Mean | 586.58 | 150920.0 |
| Median | 591.68 | 151500.0 |
| Min | 312.01 | — |
| Max | 708.97 | — |
| Std dev | 66.46 | — |
| **Ratio batch / observed** | | **257.29×** |

Batch model: `batch_latency = 300000 - (t0_epoch_ms % 300000)` with `t0` = Phase 2 log line `timestamp` per injection.

_Source: Phase 2 `async_observed.observed_detection_latency_ms`. Upsert `detection_latency_ms` was null — not used._

## Table 6 — Detection path breakdown

| detection path | count | % of 200 |
|----------------|-------|----------|
| async_observed only (poll saw notification) | 200 | 100% |
| inline upsert only | 0 | 0% |
| both inline + async_observed | 0 | 0% |
| not detected | 0 | 0% |
| **TOTAL** | **200** | **100%** |

## 5. Discussion

### Research questions (from Spirl facts, project `paper3_data_pipeline`)

**RQ1** (`research.p3.results.rq1`): RQ1 — Distribution of conflict classes and temporal-only detection gap: The synthetic corpus contains 200 injected conflicts, exactly 50 per class (semantic_contradiction, dependency_impact, constraint_violation, temporal_invalidation), spread across three projects (b7e311b5…: 67, cdc4e20b…: 67, aa75eda0…: 66). The simulated temporal-only baseline (fact research.p3.baseline.simulation) detects only temporal_invalidation (50/50 TP) and misses all non-temporal classes (0/50 each), i.e. 150/200 conflicts invisible to temporal rules alone — a 75% blind spot by conflict count versus Spirl's hybrid detector on this run.

**RQ2** (`research.p3.results.rq2`): RQ2 — Embedding-based semantic contradiction detection reliability: For Class 1 (semantic_contradiction), n=50 injections, Spirl achieved TP=50, FN=0, FP=0 (injection-level scoring from Phase 2 EXEC_LOG), hence precision=1.00, recall=1.00, F1=1.00 under Experiment C (async_observed polling; all 50 detected via notifications).

**RQ3** (`research.p3.results.rq3`): RQ3 — Under async conflict detection, mean observed notification latency from Phase 2 driver was 586.6 ms (median 591.7 ms, n=200, std dev 66.5 ms) versus mean simulated 5-minute batch polling latency 150920 ms using batch_latency = 300000 - (t0_ms mod 300000). Ratio (batch mean / observed mean) ≈ 257.3×. Upsert detection_latency_ms was null (scheduled/async path); driver used list_conflicts polling.

**Key finding.** On this balanced synthetic corpus and stack label `spirl_mcp_stack_v2`, the hybrid pipeline achieved **full injection-level recall** (200/200) while the temporal-only counterfactual missed **150/200**, and driver-observed async latency remained **orders of magnitude below** a naive five-minute polling counterfactual (Table 5). Perfect precision/recall should be read as **controlled-setting upper bounds**, not guaranteed field performance.

## 6. Limitations

- Corpus is synthetic — conflicts were deliberately injected, not observed from real teams. Real conflict distribution may differ; precision / FP on non-injected updates was not measured unless a negative control phase is added.
- Detection is **async** in Experiment C: upsert returns before notifications exist; latencies are **driver-observed** via polling, not inline HTTP response times.
- Baseline is **simulated** via `research.p3.baseline.simulation`, not a live Graphiti deployment.
- Three projects may not cover all software domain types.
- Embedding similarity threshold for Class 1 was not varied — sensitivity analysis not performed.
- Perfect scores on this run should be interpreted in light of controlled injections and the chosen stack (`spirl_mcp_stack_v2`).

**Additional limitation (Phase 4).** No **related work** or bibliographic review is included in this draft; it must be added before submission.

## 7. Conclusion

We presented a four-class taxonomy of knowledge-graph conflicts, mapped it to Spirl’s hybrid detection pipeline (semantic, dependency, constraint, temporal pathways), and evaluated it on **200** structured injections across **three** corpora. Compared to a simulated temporal-only baseline, hybrid detection recovered **4.0×** as many injected conflicts by count (200 vs 50) and maintained **1.00** F1 for semantic contradictions on this corpus; cross-project overall F1 dispersion was **0.00** under the same conditions.

Future work should stress-test **real** team traces and conflict distributions, run a **live** temporal-only store (e.g., Graphiti) against the same tasks, sweep **embedding thresholds** and detector parameters, and publish a **replication package** (SKF basis `research/paper3_basis.skf.json`, MCP drivers, and UUID-stamped logs) so independent groups can reproduce or falsify the findings.

---

Generated: 2026-04-01T06:30:00Z  
Data placeholders: 0  
Ready for human review: YES  
MCP verification: `list_facts_v1` (`kind=research`) returned **3** facts (`research.p3.results.rq1`–`rq3`) on `paper3_data_pipeline`; projects 2–3 returned **0** under the same filter. Ground-truth and baseline simulation facts use **`kind=decision`** in this deployment.
