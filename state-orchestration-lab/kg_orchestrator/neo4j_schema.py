"""Read Neo4j node label / property names from environment (safe identifiers only)."""

from __future__ import annotations

import os
import re

_LABEL = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
_PROP = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")
_REL = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _get(name: str, default: str, pat: re.Pattern[str]) -> str:
    v = os.environ.get(name, default).strip()
    if not pat.match(v):
        raise ValueError(f"Invalid {name}={v!r} (allowed: {pat.pattern})")
    return v


def fact_label() -> str:
    return _get("NEO4J_FACT_LABEL", "Fact", _LABEL)


def key_property() -> str:
    return _get("NEO4J_KEY_PROPERTY", "key", _PROP)


def body_property() -> str:
    return _get("NEO4J_BODY_PROPERTY", "body", _PROP)


def valid_from_property() -> str:
    return _get("NEO4J_VALID_FROM_PROPERTY", "valid_from", _PROP)


def valid_until_property() -> str:
    return _get("NEO4J_VALID_UNTIL_PROPERTY", "valid_until", _PROP)


def embedding_property() -> str | None:
    v = os.environ.get("NEO4J_EMBEDDING_PROPERTY", "").strip()
    if not v:
        return None
    if not _PROP.match(v):
        raise ValueError(f"Invalid NEO4J_EMBEDDING_PROPERTY={v!r}")
    return v


def inbound_rel_types() -> list[str]:
    """Comma-separated, e.g. DEPENDS_ON,USES,IMPLEMENTS."""
    raw = os.environ.get("NEO4J_INBOUND_REL_TYPES", "DEPENDS_ON,USES,IMPLEMENTS")
    types = [t.strip() for t in raw.split(",") if t.strip()]
    for t in types:
        if not _REL.match(t):
            raise ValueError(f"Invalid relationship type {t!r}")
    return types
