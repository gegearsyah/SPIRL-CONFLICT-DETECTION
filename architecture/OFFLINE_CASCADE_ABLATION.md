# Appendix G — Offline Cascade Ablation

This appendix moves the Offline Cascade Ablation out of the main body to
keep the main body focused on the deployed-system narrative. The analysis
is retained here without loss of evidence.

In parallel with the live RDL run, we operate a controlled offline harness
(`state-orchestration-lab`) that mirrors the documented cascade architecture
on the same corpus's semantic contradiction slice (40 contradiction
proposals, 26 benign controls). Stage 1–4 engines run the temporal,
ontology-numeric, and dependency prototypes; Stage 4 semantic constraint NLI
is a no-op stub offline. Stage 5 uses the progressive
`spiral_semantic_stages` verifier (retrieval + SparseCL rerank optional + NLI
gates) under MiniLM retrieval without the live LLM judge. This isolates
verifier-side behaviour while preserving cascade shape.

Seven configurations (A–G) extend the verifier by progressively adding
bidirectional NLI, contradiction margin gates, soft predicate overlap,
SparseCL reranking, and a larger multi-dataset cross-encoder. The full
configuration table is the `ablation_sweep_summary.tex` artifact shipped
alongside the paper source.

**Reading the ablation.** Configurations A–C retain higher recall but pay a
large benign false-positive rate on this slice (many benign proposals look
locally entailed relative to retrieved MiniLM neighbours). Adding the soft
predicate gate in D sharply reduces benign errors, but it also collapses
recall from 32 true positives to 11 by rejecting contradiction candidates
whose retrieval evidence is semantically valid but predicate-overlap-poor in
the offline MiniLM slice. The saved sweep artifact records identical D–G
headline scores, so we interpret E–G conservatively: once the predicate gate
is active, this offline regime is gate-dominated and the saved reranker /
encoder changes do not produce measurable downstream recovery in the
reported slice. We therefore do *not* claim that SparseCL or the WANLI-tuned
encoder are useless in general; only that they do not overcome the
gate-dominated bottleneck in this saved harness result.

**Headline takeaway.** The gap between the best offline F1 (0.735,
Config A) and the live mixed-workload F1 (0.9818) isolates the live Stage 5
judge's contribution: the cascade shape and NLI gates alone are
insufficient, and the deployed LLM judge is load-bearing.
