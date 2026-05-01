"""
NLI cross-encoder — Stage 2 (matches Spiral `backend/app/services/nli_service.py`).

Probabilities feed margin + bidirectional gates in `pipeline.py`.
Model name: `NLI_MODEL_NAME` env (via SpiralSemanticSettings).
"""

from __future__ import annotations

import logging
import math
from typing import Any, Literal, NamedTuple

log = logging.getLogger("spiral_semantic_stages.nli")

NLILabel = Literal["contradiction", "entailment", "neutral"]


class NLIResult(NamedTuple):
    label: NLILabel
    confidence: float
    probs: dict[str, float]


_model = None
_model_load_attempted = False
_active_model_name: str | None = None


def _model_name_from_settings() -> str:
    try:
        from .settings import get_settings

        return str(get_settings().nli_model_name).strip() or "cross-encoder/nli-deberta-v3-base"
    except Exception:
        return "cross-encoder/nli-deberta-v3-base"


def _get_model():
    global _model, _model_load_attempted, _active_model_name

    if _model is not None:
        return _model
    if _model_load_attempted:
        return None

    _model_load_attempted = True
    try:
        from sentence_transformers import CrossEncoder

        name = _model_name_from_settings()
        log.info("Loading NLI model: %s", name)
        _model = CrossEncoder(name)
        _active_model_name = name
        log.info("NLI model loaded successfully")
        return _model
    except Exception as exc:
        log.warning("Failed to load NLI model: %s", exc)
        return None


def reset_nli_cache_for_tests() -> None:
    global _model, _model_load_attempted, _active_model_name
    _model = None
    _model_load_attempted = False
    _active_model_name = None


def _nli_raw_scores(text_a: str, text_b: str) -> Any | None:
    model = _get_model()
    if model is None:
        return None
    try:
        scores = model.predict([(text_a, text_b)])
        if scores is None:
            return None
        return scores[0] if hasattr(scores[0], "__len__") else scores
    except Exception as exc:
        log.warning("NLI classification failed: %s", exc)
        return None


NLI_CONTRADICTION_THRESHOLD_LEGACY = 0.7


def classify_pair_probs(text_a: str, text_b: str) -> dict[str, float] | None:
    score_row = _nli_raw_scores(text_a, text_b)
    if score_row is None:
        return None
    if not hasattr(score_row, "__len__") or len(score_row) != 3:
        return None
    label_map = {0: "contradiction", 1: "entailment", 2: "neutral"}
    logits = [float(x) for x in score_row]
    max_logit = max(logits)
    exps = [math.exp(x - max_logit) for x in logits]
    total = sum(exps)
    probs = [e / total for e in exps]
    return {label_map[i]: probs[i] for i in range(3)}


def classify_pair(text_a: str, text_b: str) -> NLIResult | None:
    """Full NLI result with softmax probs (for margin gating)."""
    score_row = _nli_raw_scores(text_a, text_b)
    if score_row is None:
        return None

    label_map = {0: "contradiction", 1: "entailment", 2: "neutral"}
    if hasattr(score_row, "__len__") and len(score_row) == 3:
        logits = [float(x) for x in score_row]
        max_logit = max(logits)
        exps = [math.exp(x - max_logit) for x in logits]
        total = sum(exps)
        prob_list = [e / total for e in exps]
        best_idx = prob_list.index(max(prob_list))
        confidence = prob_list[best_idx]
        label = label_map.get(best_idx, "neutral")
        probs = {
            "contradiction": prob_list[0],
            "entailment": prob_list[1],
            "neutral": prob_list[2],
        }
        return NLIResult(label=label, confidence=confidence, probs=probs)

    confidence = float(score_row)
    label: NLILabel = "contradiction" if confidence > NLI_CONTRADICTION_THRESHOLD_LEGACY else "neutral"
    probs = {
        "contradiction": confidence if label == "contradiction" else 1.0 - confidence,
        "entailment": 0.0,
        "neutral": 1.0 - confidence if label == "contradiction" else confidence,
    }
    return NLIResult(label=label, confidence=confidence, probs=probs)


def nli_margin(probs: dict[str, float]) -> float:
    c = float(probs.get("contradiction", 0))
    nxt = max(float(probs.get("entailment", 0)), float(probs.get("neutral", 0)))
    return c - nxt


def nli_available() -> bool:
    return _get_model() is not None
