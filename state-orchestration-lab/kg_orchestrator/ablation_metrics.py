"""Macro precision / recall / F1 over conflict classes (Paper 3 style)."""

from __future__ import annotations

CONFLICT_CLASSES = (
    "semantic_contradiction",
    "dependency_impact",
    "constraint_violation",
    "temporal_invalidation",
)


def macro_prf1(
    gold_classes: list[str],
    predicted_sets: list[set[str]],
) -> dict[str, float | dict[str, dict[str, float]]]:
    """
    One gold label per row; predictions are sets of conflict_class strings fired by the lab.
    """
    per: dict[str, dict[str, float]] = {}
    precisions: list[float] = []
    recalls: list[float] = []
    f1s: list[float] = []

    for c in CONFLICT_CLASSES:
        tp = fp = fn = 0
        for g, pred in zip(gold_classes, predicted_sets):
            in_p = c in pred
            is_g = g == c
            if is_g and in_p:
                tp += 1
            elif is_g and not in_p:
                fn += 1
            elif not is_g and in_p:
                fp += 1
        p_c = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        r_c = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f_c = (
            2 * p_c * r_c / (p_c + r_c) if (p_c + r_c) > 0 else 0.0
        )
        per[c] = {"precision": p_c, "recall": r_c, "f1": f_c, "tp": float(tp), "fp": float(fp), "fn": float(fn)}
        precisions.append(p_c)
        recalls.append(r_c)
        f1s.append(f_c)

    n_cls = len(CONFLICT_CLASSES)
    return {
        "macro_precision": sum(precisions) / n_cls,
        "macro_recall": sum(recalls) / n_cls,
        "macro_f1": sum(f1s) / n_cls,
        "per_class": per,
    }
