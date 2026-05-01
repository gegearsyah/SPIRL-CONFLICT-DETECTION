"""
Optional isotonic calibration (Spiral `cosine_calibrator.py`).

In the lab package we do not pull OpenRouter embedding + STS-B fit by default:
`annotate_calibrated_scores` is a no-op here so the pipeline shape matches Spiral
without extra dependencies. When you need parity, calibrate offline and set
`calibrated_similarity` on candidates before Stage 2, or extend this module.
"""

from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger("spiral_semantic_stages.calibration")


def annotate_calibrated_scores(candidates: list[dict[str, Any]]) -> None:
    """Spiral attaches `calibrated_similarity` when the backend calibrator is ready."""

    _ = candidates
    log.debug("Lab calibrator: passthrough (no annotation)")
