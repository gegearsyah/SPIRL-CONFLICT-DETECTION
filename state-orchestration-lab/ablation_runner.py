#!/usr/bin/env python3
"""
Ablation runner — mixed-workload evaluation through the hybrid cascade lab.

For each AblationConfig × each proposal:
  1. Reset NLI / SparseCL caches for the config
  2. Retrieve neighbors from the local embedding index (Stage 5 retrieval)
  3. Run ``run_cascade_lab`` (Stages 1--5 + arbitration; Spiral v2.0-hybrid-resplit shape)
  4. Record post-arbitration conflict count, cascade_trace summary, latency
  5. Aggregate TP/FP/FN/TN and macro metrics
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from ablation_configs import AblationConfig
from corpus_loader import load_all_proposals, load_baseline_facts
from embedding_index import EmbeddingIndex

log = logging.getLogger("ablation.runner")


@dataclass
class ProposalResult:
    """Result of evaluating one proposal under one config."""

    config_name: str
    proposal_id: str
    proposal_key: str
    proposal_body: str
    ground_truth: str  # "conflict" or "benign"
    predicted: str  # "conflict" or "benign"
    detected: bool  # did the pipeline emit a semantic_contradiction?
    latency_ms: float
    neighbor_count: int
    conflict_details: list[dict[str, Any]] = field(default_factory=list)
    trace: dict[str, Any] = field(default_factory=dict)


@dataclass
class ConfigResult:
    """Aggregated results for one config across all proposals."""

    config: AblationConfig
    proposals: list[ProposalResult]

    @property
    def tp(self) -> int:
        return sum(1 for p in self.proposals if p.ground_truth == "conflict" and p.detected)

    @property
    def fp(self) -> int:
        return sum(1 for p in self.proposals if p.ground_truth == "benign" and p.detected)

    @property
    def fn(self) -> int:
        return sum(1 for p in self.proposals if p.ground_truth == "conflict" and not p.detected)

    @property
    def tn(self) -> int:
        return sum(1 for p in self.proposals if p.ground_truth == "benign" and not p.detected)

    @property
    def precision(self) -> float:
        denom = self.tp + self.fp
        return self.tp / denom if denom > 0 else 0.0

    @property
    def recall(self) -> float:
        denom = self.tp + self.fn
        return self.tp / denom if denom > 0 else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) > 0 else 0.0

    @property
    def mean_latency_ms(self) -> float:
        if not self.proposals:
            return 0.0
        return sum(p.latency_ms for p in self.proposals) / len(self.proposals)

    def to_summary_dict(self) -> dict[str, Any]:
        return {
            "config": self.config.name,
            "description": self.config.description,
            "nli_model": self.config.nli_model_name,
            "bidirectional": self.config.nli_bidirectional_enabled,
            "margin": self.config.nli_contradiction_margin_threshold,
            "reverse_margin_relaxed": self.config.nli_contradiction_reverse_margin_threshold,
            "sparsecl_everify": self.config.sparsecl_everify_enabled,
            "sparsecl": self.config.sparsecl_everify_enabled,
            "predicate_gate": self.config.nli_predicate_overlap_threshold,
            "predicate_overlap_mode": self.config.nli_predicate_overlap_mode,
            "total": len(self.proposals),
            "conflicts": sum(1 for p in self.proposals if p.ground_truth == "conflict"),
            "benign": sum(1 for p in self.proposals if p.ground_truth == "benign"),
            "TP": self.tp,
            "FP": self.fp,
            "FN": self.fn,
            "TN": self.tn,
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
            "f1": round(self.f1, 4),
            "mean_latency_ms": round(self.mean_latency_ms, 1),
        }


def _apply_config_to_settings(config: AblationConfig):
    """Create a SpiralSemanticSettings with the config's overrides."""
    from spiral_semantic_stages.settings import SpiralSemanticSettings

    overrides = config.to_settings_overrides()
    # Build settings directly with overrides (bypasses env file for sweep fields)
    return SpiralSemanticSettings(**overrides)


def _reset_model_caches():
    """Reset NLI and SparseCL model caches so the next call loads the config's model."""
    from spiral_semantic_stages.nli import reset_nli_cache_for_tests
    from spiral_semantic_stages.sparsecl import reset_sparsecl_cache_for_tests

    reset_nli_cache_for_tests()
    reset_sparsecl_cache_for_tests()


def run_single_config(
    config: AblationConfig,
    proposals: list[dict[str, Any]],
    index: EmbeddingIndex,
    *,
    baseline_rows: list[dict[str, Any]],
    limit: int = 0,
    retrieval_top_k: int = 10,
    retrieval_threshold: float = 0.35,
) -> ConfigResult:
    """Run all proposals through the hybrid cascade lab (Stages 1–5 + arbitration)."""
    from kg_orchestrator.cascade_lab import run_cascade_lab

    _reset_model_caches()
    settings = _apply_config_to_settings(config)

    if limit > 0:
        proposals = proposals[:limit]

    results: list[ProposalResult] = []
    total = len(proposals)

    for i, proposal in enumerate(proposals, 1):
        key = proposal["key"]
        body = proposal["body"]
        label = proposal["label"]

        neighbors = index.retrieve_neighbors(
            body,
            top_k=retrieval_top_k,
            threshold=retrieval_threshold,
            exclude_keys={key},
        )

        emb = index.embed_text(body).tolist()
        trace: dict[str, Any] = {}
        t0 = time.perf_counter()
        cascade_out = run_cascade_lab(
            proposal_key=key,
            proposal_body=body,
            proposal_embedding=emb,
            baseline_rows=baseline_rows,
            neighbor_dicts=neighbors,
            semantic_settings=settings,
            execution_context="preflight",
            conflict_execution_profile="research",
        )
        latency = (time.perf_counter() - t0) * 1000

        conflicts = cascade_out.get("conflicts") or []
        detected = len(conflicts) > 0
        predicted = "conflict" if detected else "benign"

        trace["cascade_lab"] = {
            "final_conflict_type": cascade_out.get("final_conflict_type"),
            "winning_detector_plane": cascade_out.get("winning_detector_plane"),
            "preflight_terminal": cascade_out.get("preflight_terminal"),
            "prune_set_size": len(cascade_out.get("prune_set") or set()),
        }
        trace["cascade_trace"] = cascade_out.get("cascade_trace") or {}
        trace["semantic_trace"] = cascade_out.get("semantic_trace") or {}
        trace["lane_verdicts"] = cascade_out.get("lane_verdicts") or {}

        marker = "✓" if (detected == (label == "conflict")) else "✗"
        log.info(
            "[%s] %s %d/%d  key=%s  label=%s  predicted=%s  neighbors=%d  arb_conflicts=%d  %.0fms",
            marker,
            config.name,
            i, total,
            key,
            label,
            predicted,
            len(neighbors),
            len(conflicts),
            latency,
        )

        results.append(ProposalResult(
            config_name=config.name,
            proposal_id=proposal.get("proposal_id", i),
            proposal_key=key,
            proposal_body=body[:200],
            ground_truth=label,
            predicted=predicted,
            detected=detected,
            latency_ms=latency,
            neighbor_count=len(neighbors),
            conflict_details=conflicts,
            trace=trace,
        ))

    return ConfigResult(config=config, proposals=results)


def run_sweep(
    configs: list[AblationConfig],
    *,
    limit: int = 0,
    skip_embedding: bool = False,
    retrieval_top_k: int = 10,
    retrieval_threshold: float = 0.35,
) -> list[ConfigResult]:
    """Run the full ablation sweep across all configs."""

    # Load corpus
    facts = load_baseline_facts()
    proposals = load_all_proposals()
    log.info("Corpus: %d baseline facts, %d proposals", len(facts), len(proposals))

    # Build embedding index
    index = EmbeddingIndex(facts)
    index.build_or_load(force=not skip_embedding and False)  # False = use cache if available

    all_results: list[ConfigResult] = []
    for config in configs:
        log.info("\n{'='*60}")
        log.info("Config: %s", config.name)
        log.info("  %s", config.description)
        log.info("  NLI model: %s", config.nli_model_name)
        log.info("{'='*60}")

        result = run_single_config(
            config,
            proposals,
            index,
            baseline_rows=facts,
            limit=limit,
            retrieval_top_k=retrieval_top_k,
            retrieval_threshold=retrieval_threshold,
        )
        all_results.append(result)

        summary = result.to_summary_dict()
        log.info(
            "\n  %s  TP=%d FP=%d FN=%d TN=%d  P=%.3f R=%.3f F1=%.3f  latency=%.0fms",
            config.name,
            summary["TP"], summary["FP"], summary["FN"], summary["TN"],
            summary["precision"], summary["recall"], summary["f1"],
            summary["mean_latency_ms"],
        )

    return all_results
