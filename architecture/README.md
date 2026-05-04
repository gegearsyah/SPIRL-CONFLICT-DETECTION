# Architecture: offline ablation + live cascade shape

This folder summarizes the **reference architecture** others can reuse on their own knowledge graph.

For the paper claim-to-artifact map, see [`../PAPER_RESULTS_GUIDE.md`](../PAPER_RESULTS_GUIDE.md).

## What is in this release vs. the live product

This release contains:

- the paper-facing RDL/TAL evaluation artifacts,
- the offline cascade / ablation lab,
- replay and metric scripts.

It does **not** contain the full Spirl production backend. The paper's live-stack claims about MCP/FastAPI routing, governance v3b knobs, and preflight/post-write integration are implemented in a separate application repository. This folder explains the reusable architecture and offline evidence that travel with the publication bundle.

## 1. Offline cascade + ablation sweep (Neo4j-optional)

The runnable package is [`../state-orchestration-lab/`](../state-orchestration-lab/README.md):

- **Hybrid cascade** (`kg_orchestrator/cascade_lab.py`, `cascade_arbitration.py`): cost-ascending stages, temporal-only prune set, plane merge, arbitration — aligned with the paper’s staged governance story.
- **Ablation sweep** (`run_ablation_sweep.py`, `ablation_runner.py`, `ablation_configs.py`): sweeps NLI / predicate / SparseCL settings on the RDL semantic slice (lists under `real-data-lab/`).
- **Governance log replay** (`replay_governance_log.py`): replay JSONL logs against your Aura / local Neo4j with `--basis-path` pointing at your SKF / fact export.

Start from `state-orchestration-lab/README.md` for `.env`, `pip install -r requirements-*.txt`, and probe commands.

## 2. Offline ablation narrative (paper Appendix G)

See [`OFFLINE_CASCADE_ABLATION.md`](OFFLINE_CASCADE_ABLATION.md) for the seven-configuration (A–G) interpretation and the headline takeaway (offline F1 vs live judge).

## 3. Live-stack constants and provenance

Wave~4 governance thresholds, leakage notes, and calibration provenance for the **live** RDL evaluation are in the bundled corpus:

- [`../real-data-lab/research/wave4_constants_provenance.md`](../real-data-lab/research/wave4_constants_provenance.md)

The **full production** Spirl implementation (MCP, FastAPI, governance v3b knobs) lives in a separate application repository; this bundle intentionally ships the **evaluation + offline lab** slice so the artifact package stays cloneable without the entire product tree.

## 4. Adapting to your knowledge graph

Expect to change:

- Neo4j **labels** and **key property** (see `state-orchestration-lab` probe + `.env` examples).
- **SKF / fact JSON** shape and import path (`import_real_data_lab_skf_mcp.py`, `paper3_basis.skf.json` patterns under `research/`).
- **Spirl project UUIDs** and `api_base` in [`.spirl/config.example.json`](../.spirl/config.example.json) → copy to `.spirl/config.json` (gitignored).

Your graph schema and constraint vocabulary will differ from Backstage/GitLab-style RDL; the **scripts and evaluation contract** are the reusable shell — the paper is the map.
