"""Optional NLI via sentence-transformers CrossEncoder (install requirements-eval.txt)."""

from __future__ import annotations

import os
from typing import Callable


def try_cross_encoder_nli(
    model_name: str | None = None,
) -> Callable[[str, str], bool] | None:
    """
    Returns (premise, hypothesis) -> True if model predicts contradiction.
    None if sentence_transformers is not installed or model load fails.
    """
    model_name = model_name or os.environ.get(
        "PAPER3_CROSS_ENCODER", "cross-encoder/nli-deberta-v3-base"
    )
    try:
        from sentence_transformers import CrossEncoder
        import numpy as np
    except ImportError:
        return None

    try:
        ce = CrossEncoder(model_name)
    except Exception:
        return None

    cfg = getattr(ce.model, "config", None)
    id2label = getattr(cfg, "id2label", None) if cfg is not None else None
    contradiction_idx: int | None = None
    if isinstance(id2label, dict):
        for idx, lab in id2label.items():
            if lab is not None and "contradict" in str(lab).lower():
                contradiction_idx = int(idx)
                break
    if contradiction_idx is None:
        contradiction_idx = 0

    def nli(premise: str, hypothesis: str) -> bool:
        scores = ce.predict([(premise, hypothesis)])
        arr = np.asarray(scores)
        if arr.ndim == 2:
            arr = arr[0]
        return int(np.argmax(arr)) == contradiction_idx

    return nli
