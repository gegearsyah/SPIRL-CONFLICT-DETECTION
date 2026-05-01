from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Severity(str, Enum):
    info = "info"
    warning = "warning"
    high = "high"


class FactProposal(BaseModel):
    """Proposed fact f = (k, b, e, I) aligned with paper3 §3.1 (embedding optional for offline demo)."""

    key: str = Field(..., description="Epistemic key k")
    body: str = Field(..., description="Normalized text b")
    valid_from: datetime | None = Field(None, description="Interval start t_s")
    valid_until: datetime | None = Field(None, description="Interval end t_e")
    embedding: list[float] | None = Field(None, description="Vector e if available")
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExistingFact(BaseModel):
    key: str
    body: str
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    embedding: list[float] | None = None
    fact_id: str | None = None


class GraphContext(BaseModel):
    """Snapshot passed to engines (from Neo4j, API, or in-memory fixture)."""

    same_key_facts: list[ExistingFact] = Field(default_factory=list)
    neighbor_facts: list[ExistingFact] = Field(default_factory=list)
    inbound_dependency_sources: list[str] = Field(
        default_factory=list,
        description="Keys or ids of facts with edges into this proposal's target",
    )
    constraint_bounds: dict[str, float] = Field(
        default_factory=dict,
        description="Named numeric caps v for constraint checks (paper §3.2 axis 3)",
    )
    allowed_rel_types: set[str] | None = Field(
        default=None,
        description="If set, ontology engine can flag unknown relationship types",
    )
    multi_hop_upstream_count: int | None = Field(
        default=None,
        description="Optional: count of distinct upstream facts within k hops (filled by Neo4j accessor when enabled).",
    )


class GovernanceFinding(BaseModel):
    engine: str
    conflict_class: str
    severity: Severity
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
