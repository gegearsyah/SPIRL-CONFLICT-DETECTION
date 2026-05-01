"""Replay-only embedding fill when Neo4j nodes lack vector properties (Experiment C lab)."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kg_orchestrator.models import FactProposal, GraphContext

log = logging.getLogger("kg_orchestrator.replay_embeddings")

_st_model = None


def _get_st_model():
    global _st_model
    if _st_model is None:
        from sentence_transformers import SentenceTransformer

        _st_model = SentenceTransformer("all-MiniLM-L6-v2")
        log.info("Loaded %s for replay embedding hydration", "all-MiniLM-L6-v2")
    return _st_model


def replay_embedding_hydration_available() -> bool:
    try:
        import sentence_transformers  # noqa: F401

        return True
    except ImportError:
        return False


def ensure_fact_embeddings(
    proposal: "FactProposal",
    ctx: "GraphContext",
    *,
    enabled: bool,
) -> tuple["FactProposal", "GraphContext"]:
    """
    When enabled, embed proposal + neighbor bodies missing vectors so Stage-1 cosine
    and SparseCL can run. Does not change production Neo4j-backed paths unless called.
    """
    if not enabled or not replay_embedding_hydration_available():
        return proposal, ctx

    texts: list[str] = []
    prop_slot: int | None = None
    nb_slots: dict[int, int] = {}

    if proposal.embedding is None and (proposal.body or "").strip():
        prop_slot = len(texts)
        texts.append(proposal.body.strip())

    for i, nb in enumerate(ctx.neighbor_facts):
        if nb.embedding is None and (nb.body or "").strip():
            nb_slots[i] = len(texts)
            texts.append(nb.body.strip())

    if not texts:
        return proposal, ctx

    enc = _get_st_model()
    vecs = enc.encode(texts, convert_to_numpy=True, show_progress_bar=False)

    new_emb = proposal.embedding
    if prop_slot is not None:
        new_emb = [float(x) for x in vecs[prop_slot]]

    new_neighbors = []
    for i, nb in enumerate(ctx.neighbor_facts):
        if i in nb_slots:
            row = nb_slots[i]
            emb = [float(x) for x in vecs[row]]
            new_neighbors.append(nb.model_copy(update={"embedding": emb}))
        else:
            new_neighbors.append(nb)

    new_proposal = (
        proposal.model_copy(update={"embedding": new_emb})
        if new_emb is not None
        else proposal
    )
    new_ctx = ctx.model_copy(update={"neighbor_facts": new_neighbors})
    return new_proposal, new_ctx
