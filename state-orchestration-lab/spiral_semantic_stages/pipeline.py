"""
Spiral semantic contradiction stages without Neo4j/pgvector retrieval.

Matches `backend/app/services/semantic_checker.py` for Stages 1.5–2 and the
same gating on precomputed neighbors (Stage 1 = filter + sort + limit).

Pass candidates as list[dict] with at least: key, body, similarity.
Optional: id, kind, sparsecl_* (recomputed on rerank).
"""

from __future__ import annotations

import logging
from typing import Any

from .calibration import annotate_calibrated_scores
from .nli import classify_pair, classify_pair_probs, nli_available, nli_margin
from .predicate_gate import predicate_overlap_admits
from .settings import SpiralSemanticSettings, get_settings
from .sparsecl import rerank_candidates, sparsecl_available

log = logging.getLogger("spiral_semantic_stages.pipeline")


def _sparsecl_rerank_and_filter(
    query_text: str,
    candidates: list[dict[str, Any]],
    *,
    cfg: SpiralSemanticSettings,
    nli_cap: int = 5,
) -> tuple[list[dict[str, Any]], bool, dict[str, Any]]:
    meta: dict[str, Any] = {
        "sparsecl_invoked": False,
        "recall_guard_applied": False,
        "reranked_count": 0,
        "after_everify_count": 0,
        "everify_enabled": bool(cfg.sparsecl_everify_enabled),
        "sparsity_floor": float(cfg.sparsity_entailment_floor),
    }
    if not sparsecl_available(cfg):
        meta["after_everify_count"] = len(candidates)
        return candidates, False, meta

    meta["sparsecl_invoked"] = True
    reranked = rerank_candidates(query_text, candidates, settings=cfg)
    meta["reranked_count"] = len(reranked)

    if not cfg.sparsecl_everify_enabled:
        log.info(
            "SparseCL: reranked %d candidates (E-Verify filter disabled)",
            len(reranked),
        )
        meta["after_everify_count"] = len(reranked)
        return reranked, True, meta

    floor = cfg.sparsity_entailment_floor
    filtered: list[dict[str, Any]] = []
    for c in reranked:
        hoyer = c.get("sparsecl_hoyer")
        if hoyer is not None and hoyer < floor:
            log.debug(
                "E-Verify fast-path: skipping '%s' (hoyer=%.3f < %.3f)",
                c.get("key", "?"),
                hoyer,
                floor,
            )
            continue
        filtered.append(c)

    if not filtered and reranked:
        meta["recall_guard_applied"] = True
        k = max(1, min(nli_cap, len(reranked)))
        sorted_r = sorted(
            reranked,
            key=lambda c: float(c.get("sparsecl_combined", c.get("similarity") or 0)),
            reverse=True,
        )
        filtered = sorted_r[:k]
        log.warning(
            "E-Verify would drop all %d SparseCL candidates; falling back to top %d for NLI (recall guard)",
            len(reranked),
            k,
        )

    log.info(
        "SparseCL: %d candidates → %d after E-Verify filter (floor=%.2f)",
        len(reranked),
        len(filtered),
        floor,
    )

    meta["after_everify_count"] = len(filtered)
    return filtered, True, meta


def _classify_with_nli(
    fact_key: str,
    fact_body: str,
    neighbor: dict[str, Any],
    sim: float,
    proposed_kind: str | None,
    *,
    cfg: SpiralSemanticSettings,
    sparsecl_active: bool,
) -> dict[str, Any] | None:
    """Bidirectional + margin-gated NLI (Spiral `semantic_checker._classify_with_nli`)."""
    nli_threshold = cfg.nli_contradiction_confidence_threshold
    margin_threshold = cfg.nli_contradiction_margin_threshold
    bidirectional = cfg.nli_bidirectional_enabled
    forward_dominant = cfg.nli_forward_dominant_override_enabled

    neighbor_key = neighbor.get("key", "")
    neighbor_body = neighbor.get("body") or ""

    if not fact_body or not neighbor_body:
        return None

    result_ab = classify_pair(fact_body, neighbor_body)
    if result_ab is None:
        return None

    if result_ab.label in ("entailment", "neutral"):
        log.debug(
            "NLI forward filtered %s <-> %s: %s (%.3f)",
            fact_key,
            neighbor_key,
            result_ab.label,
            result_ab.confidence,
        )
        return None

    if result_ab.label == "contradiction" and result_ab.confidence < nli_threshold:
        log.debug(
            "NLI forward below threshold %s <-> %s: %.3f < %.3f",
            fact_key,
            neighbor_key,
            result_ab.confidence,
            nli_threshold,
        )
        return None

    contra_ab = result_ab.probs.get("contradiction", result_ab.confidence)
    next_best_ab = max(
        result_ab.probs.get("entailment", 0),
        result_ab.probs.get("neutral", 0),
    )
    margin_ab = float(contra_ab) - float(next_best_ab)

    if margin_threshold > 0 and margin_ab < margin_threshold:
        log.debug(
            "NLI margin gate (forward) %s <-> %s: margin=%.3f < %.3f",
            fact_key,
            neighbor_key,
            margin_ab,
            margin_threshold,
        )
        return None

    confidence = float(result_ab.confidence)
    margin_final = margin_ab
    result_ba = None
    reverse_margin_floor_used: float | None = None
    forward_dominant_applied = False

    if bidirectional:
        result_ba = classify_pair(neighbor_body, fact_body)
        if result_ba is None:
            return None

        reverse_ok = True
        margin_ba = 0.0

        if result_ba.label != "contradiction" or result_ba.confidence < nli_threshold:
            reverse_ok = False
        else:
            contra_ba = result_ba.probs.get("contradiction", result_ba.confidence)
            next_best_ba = max(
                result_ba.probs.get("entailment", 0),
                result_ba.probs.get("neutral", 0),
            )
            margin_ba = float(contra_ba) - float(next_best_ba)
            effective_reverse = margin_threshold
            if (
                cfg.nli_contradiction_reverse_margin_threshold > 0
                and float(result_ab.confidence) >= cfg.nli_forward_strong_confidence
                and margin_ab >= cfg.nli_forward_strong_margin
            ):
                effective_reverse = cfg.nli_contradiction_reverse_margin_threshold
            reverse_margin_floor_used = effective_reverse
            if margin_threshold > 0 and margin_ba < effective_reverse:
                reverse_ok = False

        if not reverse_ok:
            dom_c = float(result_ab.confidence)
            dom_m = margin_ab
            if (
                forward_dominant
                and dom_c >= cfg.nli_forward_dominant_min_confidence
                and dom_m >= cfg.nli_forward_dominant_min_margin
            ):
                forward_dominant_applied = True
                confidence = dom_c
                margin_final = dom_m
            else:
                log.debug(
                    "NLI bidirectional disagreement %s <-> %s: forward=%s(%.3f) reverse=%s(%.3f)",
                    fact_key,
                    neighbor_key,
                    result_ab.label,
                    result_ab.confidence,
                    result_ba.label,
                    result_ba.confidence,
                )
                return None
        else:
            confidence = min(float(result_ab.confidence), float(result_ba.confidence))
            margin_final = min(margin_ab, margin_ba)

    severity = "high" if confidence >= 0.90 else "medium"

    details: dict[str, Any] = {
        "key": fact_key,
        "neighbor_key": neighbor_key,
        "neighbor_body": neighbor_body[:200],
        "similarity": sim,
        "detection_method": "three_stage_pipeline",
        "nli_label": "contradiction",
        "nli_confidence": confidence,
        "nli_margin": round(margin_final, 4),
        "nli_probs_forward": {k: round(v, 4) for k, v in result_ab.probs.items()},
        "nli_bidirectional": bidirectional,
        "nli_forward_dominant_override": forward_dominant_applied,
        "proposed_kind": proposed_kind,
        "neighbor_kind": neighbor.get("kind"),
    }
    if bidirectional and reverse_margin_floor_used is not None:
        details["nli_reverse_margin_floor"] = reverse_margin_floor_used

    if sparsecl_active:
        details["sparsecl_cosine"] = neighbor.get("sparsecl_cosine")
        details["sparsecl_hoyer"] = neighbor.get("sparsecl_hoyer")
        details["sparsecl_combined"] = neighbor.get("sparsecl_combined")

    cal = neighbor.get("calibrated_similarity")
    if cal is not None:
        details["calibrated_similarity"] = cal

    if bidirectional and result_ba is not None:
        details["nli_probs_reverse"] = {k: round(v, 4) for k, v in result_ba.probs.items()}

    return {
        "conflict_type": "semantic_contradiction",
        "severity": severity,
        "summary": (
            f"Fact '{fact_key}' contradicts '{neighbor_key}' "
            f"(similarity={sim:.3f}, NLI confidence={confidence:.3f}, margin={margin_final:.3f})"
        ),
        "details": details,
        "conflicting_fact_id": neighbor.get("id"),
    }


def _emit_unverified(
    fact_key: str,
    neighbor: dict[str, Any],
    sim: float,
    proposed_kind: str | None,
    *,
    sparsecl_active: bool,
) -> dict[str, Any] | None:
    neighbor_key = neighbor.get("key", "")
    neighbor_body = neighbor.get("body") or ""

    details: dict[str, Any] = {
        "key": fact_key,
        "neighbor_key": neighbor_key,
        "neighbor_body": neighbor_body[:200],
        "similarity": sim,
        "detection_method": "embedding_only",
        "nli_label": None,
        "nli_confidence": None,
        "proposed_kind": proposed_kind,
        "neighbor_kind": neighbor.get("kind"),
    }

    if sparsecl_active:
        details["sparsecl_cosine"] = neighbor.get("sparsecl_cosine")
        details["sparsecl_hoyer"] = neighbor.get("sparsecl_hoyer")
        details["sparsecl_combined"] = neighbor.get("sparsecl_combined")

    cal = neighbor.get("calibrated_similarity")
    if cal is not None:
        details["calibrated_similarity"] = cal

    return {
        "conflict_type": "unverified_similarity",
        "severity": "info",
        "summary": (
            f"Fact '{fact_key}' is very similar to '{neighbor_key}' "
            f"(similarity={sim:.3f}) — NLI unavailable, not verified as contradiction"
        ),
        "details": details,
        "conflicting_fact_id": neighbor.get("id"),
    }


def _neighbor_trace_row(c: dict[str, Any]) -> dict[str, Any]:
    return {
        "key": c.get("key"),
        "embedding_similarity": c.get("similarity"),
        "sparsecl_cosine": c.get("sparsecl_cosine"),
        "sparsecl_hoyer": c.get("sparsecl_hoyer"),
        "sparsecl_combined": c.get("sparsecl_combined"),
        "id": c.get("id"),
        "kind": c.get("kind"),
    }


def check_semantic_contradictions_stages(
    fact_key: str,
    fact_body: str,
    candidates: list[dict[str, Any]],
    *,
    settings: SpiralSemanticSettings | None = None,
    limit: int = 10,
    proposed_kind: str | None = None,
    trace: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """
    Run Spiral-equivalent semantic stages on **pre-retrieved** neighbors.

    Stage 1 (here): drop same-key, require ``similarity >= threshold``, top-``limit``.
    Stage 1.5: SparseCL rerank + optional E-Verify (Hoyer floor + recall guard).
    Calibration: no-op in lab (see ``calibration.py``).
    Stage 1.75: predicate overlap gate (Jaccard content words).
    Stage 2: Bidirectional margin-gated NLI or unverified_similarity fallback.
    """
    cfg = settings or get_settings()
    threshold = cfg.conflict_embedding_similarity_threshold
    high_threshold = cfg.contradiction_high_severity_similarity

    if trace is not None:
        trace.clear()
        trace["fact_key"] = fact_key
        trace["stage1_threshold"] = threshold
        trace["high_severity_similarity"] = high_threshold
        trace["nli_threshold"] = cfg.nli_contradiction_confidence_threshold
        trace["nli_margin_threshold"] = cfg.nli_contradiction_margin_threshold
        trace["nli_reverse_margin_relaxed"] = cfg.nli_contradiction_reverse_margin_threshold
        trace["nli_bidirectional"] = cfg.nli_bidirectional_enabled
        trace["nli_predicate_overlap_threshold"] = cfg.nli_predicate_overlap_threshold
        trace["nli_predicate_overlap_mode"] = cfg.nli_predicate_overlap_mode

    filtered = [c for c in candidates if c.get("key") != fact_key]
    filtered = [
        c
        for c in filtered
        if float(c.get("similarity") or 0) >= threshold
    ]
    filtered.sort(key=lambda c: float(c.get("similarity") or 0), reverse=True)
    filtered = filtered[:limit]

    if trace is not None:
        trace["stage1_neighbors"] = [_neighbor_trace_row(c) for c in filtered]

    if not filtered:
        if trace is not None:
            trace["sparsecl"] = {"sparsecl_invoked": False}
            trace["stage15_neighbors"] = []
            trace["nli_evaluations"] = []
            trace["hits"] = []
        return []

    nli_cap = min(limit, 5)
    stage15, sparsecl_active, sparsecl_meta = _sparsecl_rerank_and_filter(
        fact_body,
        filtered,
        cfg=cfg,
        nli_cap=nli_cap,
    )
    if trace is not None:
        trace["sparsecl"] = sparsecl_meta
        trace["sparsecl_active"] = sparsecl_active
        trace["stage15_neighbors"] = [_neighbor_trace_row(c) for c in stage15]

    if not stage15:
        if trace is not None:
            trace["nli_evaluations"] = []
            trace["hits"] = []
        return []

    annotate_calibrated_scores(stage15)

    nli_ok = nli_available()
    results: list[dict[str, Any]] = []
    nli_trace_rows: list[dict[str, Any]] = []
    pred_thr = cfg.nli_predicate_overlap_threshold

    for neighbor in stage15:
        sim = float(neighbor.get("similarity") or 0)
        nk = neighbor.get("key", "")
        neighbor_body = neighbor.get("body") or ""

        pred_admits, pred_reason = predicate_overlap_admits(
            fact_body,
            neighbor_body,
            threshold=pred_thr,
            mode=cfg.nli_predicate_overlap_mode,
            no_rescue_floor=cfg.semantic_overlap_no_rescue_floor,
            rescue_similarity=cfg.nli_predicate_overlap_rescue_similarity,
            rescue_hoyer=cfg.nli_predicate_overlap_rescue_hoyer,
            embedding_similarity=sim,
            sparsecl_hoyer=neighbor.get("sparsecl_hoyer"),
        )
        if pred_thr > 0 and not pred_admits:
            log.debug(
                "Predicate overlap gate: skipping %s <-> %s (%s, thr=%.2f)",
                fact_key,
                nk,
                pred_reason,
                pred_thr,
            )
            if trace is not None:
                nli_trace_rows.append(
                    {
                        "neighbor_key": nk,
                        "embedding_similarity": sim,
                        "sparsecl_cosine": neighbor.get("sparsecl_cosine"),
                        "sparsecl_hoyer": neighbor.get("sparsecl_hoyer"),
                        "sparsecl_combined": neighbor.get("sparsecl_combined"),
                        "nli_probs": None,
                        "gate": "predicate_overlap_skip",
                        "predicate_gate": pred_reason,
                    }
                )
            continue

        if nli_ok:
            conflict = _classify_with_nli(
                fact_key,
                fact_body,
                neighbor,
                sim,
                proposed_kind,
                cfg=cfg,
                sparsecl_active=sparsecl_active,
            )
            if trace is not None:
                probs = classify_pair_probs(fact_body, neighbor_body)
                gate = "emitted_contradiction" if conflict is not None else "unknown"
                if conflict is None and probs is not None:
                    nli_thr = cfg.nli_contradiction_confidence_threshold
                    m_thr = cfg.nli_contradiction_margin_threshold
                    mar = nli_margin(probs)
                    best_l = max(probs, key=probs.__getitem__)
                    best_p = probs[best_l]
                    if best_l in ("entailment", "neutral"):
                        gate = "filtered_entailment_or_neutral"
                    elif best_l == "contradiction" and best_p < nli_thr:
                        gate = "below_nli_confidence_forward"
                    elif best_l == "contradiction" and m_thr > 0 and mar < m_thr:
                        gate = "below_nli_margin_forward"
                    else:
                        gate = "filtered_bidirectional_or_margin_reverse"
                elif conflict is None and probs is None:
                    gate = "nli_failed_or_unavailable"
                nli_trace_rows.append(
                    {
                        "neighbor_key": nk,
                        "embedding_similarity": sim,
                        "sparsecl_cosine": neighbor.get("sparsecl_cosine"),
                        "sparsecl_hoyer": neighbor.get("sparsecl_hoyer"),
                        "sparsecl_combined": neighbor.get("sparsecl_combined"),
                        "nli_probs": probs,
                        "gate": gate,
                    }
                )
            if conflict is not None:
                results.append(conflict)
        else:
            if trace is not None:
                gate = (
                    "unverified_emitted"
                    if sim >= high_threshold
                    else "unverified_skipped_low_similarity"
                )
                nli_trace_rows.append(
                    {
                        "neighbor_key": nk,
                        "embedding_similarity": sim,
                        "sparsecl_cosine": neighbor.get("sparsecl_cosine"),
                        "sparsecl_hoyer": neighbor.get("sparsecl_hoyer"),
                        "sparsecl_combined": neighbor.get("sparsecl_combined"),
                        "nli_probs": None,
                        "gate": gate,
                    }
                )
            if sim >= high_threshold:
                conflict = _emit_unverified(
                    fact_key,
                    neighbor,
                    sim,
                    proposed_kind,
                    sparsecl_active=sparsecl_active,
                )
                if conflict is not None:
                    results.append(conflict)

    if trace is not None:
        trace["nli_evaluations"] = nli_trace_rows
        trace["hits"] = results

    return results
