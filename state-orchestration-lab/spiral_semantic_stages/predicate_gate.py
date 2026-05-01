"""
Stage 1.75 — predicate overlap (Jaccard on content words).

Hard mode mirrors `semantic_checker._predicate_overlap_sufficient`.
Soft mode + rescue paths follow Spiral/docs/CONFLICT_DETECTION_ARCHITECTURE.md (Apr 2026).
"""

from __future__ import annotations

import re

_TOKEN_RE = re.compile(r"[a-zA-Z0-9_]+(?:\.[a-zA-Z0-9_]+)*")

_STOPWORDS = frozenset({
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "to", "of", "in", "for",
    "on", "with", "at", "by", "from", "as", "into", "through", "during",
    "before", "after", "above", "below", "between", "out", "off", "over",
    "under", "again", "further", "then", "once", "and", "but", "or", "nor",
    "not", "no", "so", "if", "than", "too", "very", "just", "about",
    "also", "its", "it", "this", "that", "these", "those", "such", "when",
    "where", "how", "what", "which", "who", "whom", "each", "every", "all",
    "both", "few", "more", "most", "other", "some", "any", "only", "own",
    "same", "up", "down", "here", "there",
})


def extract_content_words(text: str) -> set[str]:
    tokens = _TOKEN_RE.findall(text.lower())
    return {t for t in tokens if t not in _STOPWORDS and len(t) > 1}


def predicate_jaccard_score(text_a: str, text_b: str) -> float | None:
    """Jaccard on content words, or None if fail-open (empty token side)."""
    tokens_a = extract_content_words(text_a)
    tokens_b = extract_content_words(text_b)
    if not tokens_a or not tokens_b:
        return None
    union = tokens_a | tokens_b
    if not union:
        return None
    return len(tokens_a & tokens_b) / len(union)


def predicate_overlap_sufficient(text_a: str, text_b: str, threshold: float) -> bool:
    """True if Jaccard(content words) >= threshold. Fail-open if a text has no tokens."""
    score = predicate_jaccard_score(text_a, text_b)
    if score is None:
        return True
    return score >= threshold


def predicate_overlap_admits(
    text_a: str,
    text_b: str,
    *,
    threshold: float,
    mode: str,
    no_rescue_floor: float,
    rescue_similarity: float,
    rescue_hoyer: float,
    embedding_similarity: float,
    sparsecl_hoyer: float | None,
) -> tuple[bool, str]:
    """
    Spiral Apr 2026 soft gate: Jaccard pass, else hard veto or rescue via
    embedding / SparseCL Hoyer when signals are strong enough.
    """
    if threshold <= 0:
        return True, "disabled"

    score = predicate_jaccard_score(text_a, text_b)
    if score is None:
        return True, "fail_open_empty_tokens"

    if score >= threshold:
        return True, "jaccard_pass"

    mode_l = (mode or "soft").strip().lower()
    if mode_l == "hard":
        return False, "hard_veto"

    h = float(sparsecl_hoyer) if sparsecl_hoyer is not None else 0.0
    strong = embedding_similarity >= rescue_similarity or h >= rescue_hoyer

    if score < no_rescue_floor:
        return (True, "soft_rescue_below_floor") if strong else (False, "soft_veto_below_floor")

    if strong:
        return True, "soft_rescue_mid_band"
    return False, "soft_veto_mid_band"
