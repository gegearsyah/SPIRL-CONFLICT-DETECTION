# State orchestration lab

Small **reference architecture** for Paper 3: one **knowledge graph** (e.g. Neo4j Aura) as the shared source of truth, with **pluggable governance engines** (temporal, semantic, ontology/constraints, dependency) and an orchestrator that merges findings.

## Hybrid cascade (offline, architecture-aligned)

`kg_orchestrator/cascade_lab.py` + `cascade_arbitration.py` implement the **v2.0 hybrid re-split** shape from Spiral's conflict docs: serial Stages 1--5, **temporal-only** `prune_set`, plane merge, and arbitration with the same signal-contract fields used for RDL scoring. Stage 5 calls `spiral_semantic_stages` on embedding-index neighbors (no live LLM judge). **`python run_ablation_sweep.py`** sweeps NLI / predicate / SparseCL settings through this full cascade on the RDL semantic slice (`../real-data-lab` lists + SKF).

## Governance log replay (`replay_governance_log.py`)

Replays `conflict_injected` rows from a JSONL log through the local orchestrator + Neo4j (not the live Spirl MCP stack). Supports:

- **Paper 3** logs: default `--research-dir ../research` and `paper3_execution_log.experiment_C.jsonl`, basis `paper3_basis.skf.json`
- **Real Data Lab** logs: point at `../real-data-lab/research/real_data_lab_execution_log.jsonl` and pass **`--basis-path`** to the project SKF (bodies live under top-level `facts[].value`)

RDL rows only list the proposed key in `result.fact_keys`; the script merges **`based_on_facts`** and **`proposed_fact_key`** into the cohort so baseline neighbors load.

```bash
cd "Beyond Temporal Contradiction/state-orchestration-lab"

# Paper 3 — parse only (no Neo4j)
python replay_governance_log.py --dry-run --limit 10

# Paper 3 — against Aura (needs .env + schema)
python replay_governance_log.py --limit 20

# Real Data Lab — dry-run (check cohort expansion)
python replay_governance_log.py \
  --research-dir ../real-data-lab/research \
  --log-name real_data_lab_execution_log.jsonl \
  --basis-path "../real-data-lab/Project Core Platform.skf.json" \
  --dry-run --limit 10

# Backwards-compatible entry point (same CLI)
python replay_experiment_c.py --dry-run --limit 10
```

**Note:** The lab is a **subset** of full Spirl (no MCP). Semantic replay can hydrate missing vectors with MiniLM; Neo4j may still differ from what Spirl evaluated live.

---

## What to do (after `pip install` + `.env`)

All commands run **inside** `Beyond Temporal Contradiction/state-orchestration-lab/`.

### 1) Prove Aura works — schema probe

```bash
cd "Beyond Temporal Contradiction/state-orchestration-lab"
python run_neo4j_probe.py
```

You should see `OK: connectivity verified`, then a list of **labels** and **node counts**, plus sample **property keys** for a few labels.

### 2) Match your real graph (if probe shows something other than `:Fact` + `key`)

Edit `.env` and uncomment/set:

- `NEO4J_FACT_LABEL` — node label for facts (exact name from probe)
- `NEO4J_KEY_PROPERTY` — property holding the epistemic key
- `NEO4J_BODY_PROPERTY`, `NEO4J_VALID_FROM_PROPERTY`, `NEO4J_VALID_UNTIL_PROPERTY` if yours differ
- `NEO4J_INBOUND_REL_TYPES` — comma-separated relationship types pointing **into** the target fact

Re-run step 1 if needed.

### 3) Run governance on one real key

Pick any `key` value that exists in your DB (from Neo4j Browser or your app):

```bash
python run_aura_governance.py --key your.actual.key
```

Optional ontology demo (paper §3.2 axis 3):

```bash
python run_aura_governance.py --key your.actual.key --bounds max_replicas:10 --body "We run 99 replicas."
```

If you see `same_key_facts in DB: 0` and you know data exists, go back to step 2 — label/property names still wrong.

### 4) Offline demo (no database)

```bash
python run_demo.py
```

## Map to `paper/paper3_neurips.tex`

| Engine | Paper §3.2 | Code |
|--------|------------|------|
| Temporal | Axis 1 | `engines/temporal.py` |
| Semantic (progressive) | Axis 2 — SparseCL, predicate gate, bidirectional NLI | `engines/progressive_semantic.py` |
| Semantic (legacy ablation) | Baseline cosine + optional unidirectional CE | `engines/semantic.py` |
| Ontology | Axis 3 + rel types | `engines/ontology.py` |
| Dependency | Axis 4 | `engines/dependency.py` |

`GovernanceOrchestrator.evaluate_async` runs engines **concurrently** (thread pool). Replay and Aura helpers call it via `asyncio.run(...)`.

## Zep

Zep is **not** used here. It stays **related work** in the paper unless you add a separate Zep API driver later.

## Spiral-aligned semantic pipeline

**Governance replay** (`replay_governance_log.py`) and **Aura governance** default to `ProgressiveSemanticContradictionEngine` when `spiral_semantic_stages` + NLI load successfully (`pip install -r requirements.txt -r requirements-eval.txt -r requirements-spiral-stages.txt`). Set `PAPER3_LEGACY_SEMANTIC=1` to force `SemanticContradictionEngine` + cross-encoder (or `--nli-oracle` for smoke tests).

- Folder: [`spiral_semantic_stages/`](spiral_semantic_stages/README.md)
- Entry point: `check_semantic_contradictions_stages(...)` on pre-retrieved neighbor dicts; `candidates_from_neighbors(...)` bridges `GraphContext`.

## Next steps (optional)

- Ensure cohort neighbors carry `embedding` in Neo4j (`NEO4J_EMBEDDING_PROPERTY`) so Stage-1 cosine gating can run.
- Add `scripts/replay_paper3_jsonl.py` against `Beyond Temporal Contradiction/research/paper3_*.jsonl`.
