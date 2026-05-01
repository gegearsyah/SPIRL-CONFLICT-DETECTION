"""Read GraphContext from Neo4j Aura / self-hosted — wire your node labels and property names."""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any

from kg_orchestrator.models import ExistingFact, GraphContext
from kg_orchestrator import neo4j_schema as schema

try:
    from neo4j import GraphDatabase
except ImportError:
    GraphDatabase = None  # type: ignore[misc,assignment]


def _parse_dt(v: Any) -> datetime | None:
    if v is None:
        return None
    if isinstance(v, datetime):
        return v
    if isinstance(v, str):
        return datetime.fromisoformat(v.replace("Z", "+00:00"))
    return None


class Neo4jGraphAccessor:
    """
    Parameterize Cypher to match your schema. Defaults assume logical keys on :Fact nodes;
    adjust QUERIES after introspecting Spiral/Neo4j labels.
    """

    def __init__(self, uri: str | None = None, user: str | None = None, password: str | None = None):
        uri = uri or os.environ.get("NEO4J_URI")
        user = user or os.environ.get("NEO4J_USER", "neo4j")
        password = password or os.environ.get("NEO4J_PASSWORD", "")
        if not uri or not password:
            raise ValueError("Set NEO4J_URI and NEO4J_PASSWORD (e.g. from .env)")
        if GraphDatabase is None:
            raise ImportError("pip install neo4j")
        self._driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self) -> None:
        self._driver.close()

    def load_context_for_key(
        self,
        epistemic_key: str,
        *,
        project_id: str | None = None,
        constraint_bounds: dict[str, float] | None = None,
    ) -> GraphContext:
        """
        Example query — replace MATCH pattern with your real graph model.
        """
        same_key: list[ExistingFact] = []
        neighbors: list[ExistingFact] = []
        inbound: list[str] = []

        lbl = schema.fact_label()
        kp = schema.key_property()
        bp = schema.body_property()
        vf = schema.valid_from_property()
        vu = schema.valid_until_property()
        rel_union = "|".join(schema.inbound_rel_types())

        with self._driver.session() as session:
            # Same-key facts (validity overlap checked in temporal engine)
            q1 = f"""
                MATCH (f:`{lbl}`)
                WHERE f.`{kp}` = $key
                RETURN elementId(f) AS id, f.`{kp}` AS key, f.`{bp}` AS body,
                       f.`{vf}` AS valid_from, f.`{vu}` AS valid_until
                LIMIT 50
                """
            r = session.run(q1, key=epistemic_key)
            for row in r:
                same_key.append(
                    ExistingFact(
                        fact_id=row["id"],
                        key=row["key"],
                        body=row["body"] or "",
                        valid_from=_parse_dt(row["valid_from"]),
                        valid_until=_parse_dt(row["valid_until"]),
                    )
                )

            # Vector neighbors: add db.index.vector.queryNodes when your index name is known.

            q2 = f"""
                MATCH (src:`{lbl}`)-[r:{rel_union}]->(t:`{lbl}`)
                WHERE t.`{kp}` = $key
                RETURN DISTINCT src.`{kp}` AS sk
                LIMIT 100
                """
            r2 = session.run(q2, key=epistemic_key)
            for row in r2:
                if row["sk"]:
                    inbound.append(row["sk"])

            multi_hop: int | None = None
            try:
                kh = int(os.environ.get("NEO4J_DEPENDENCY_KHOP", "0"))
            except ValueError:
                kh = 0
            if 1 <= kh <= 5:
                q3 = f"""
                    MATCH (t:`{lbl}`)
                    WHERE t.`{kp}` = $key
                    MATCH (u:`{lbl}`)-[*1..{kh}]->(t)
                    RETURN count(DISTINCT u) AS c
                    """
                row3 = session.run(q3, key=epistemic_key).single()
                if row3 is not None and row3.get("c") is not None:
                    multi_hop = int(row3["c"])

        return GraphContext(
            same_key_facts=same_key,
            neighbor_facts=neighbors,
            inbound_dependency_sources=inbound,
            constraint_bounds=constraint_bounds or {},
            multi_hop_upstream_count=multi_hop,
        )

    def fetch_facts_by_keys(self, keys: list[str]) -> dict[str, ExistingFact]:
        """Load at most one node per epistemic key (first match). Optional embedding from env."""
        uniq = list(dict.fromkeys(k for k in keys if k))
        if not uniq:
            return {}

        lbl = schema.fact_label()
        kp = schema.key_property()
        bp = schema.body_property()
        vf = schema.valid_from_property()
        vu = schema.valid_until_property()
        emb_prop = schema.embedding_property()
        emb_sel = f", f.`{emb_prop}` AS embedding" if emb_prop else ""

        q = f"""
            MATCH (f:`{lbl}`)
            WHERE f.`{kp}` IN $keys
            RETURN elementId(f) AS id, f.`{kp}` AS key, f.`{bp}` AS body,
                   f.`{vf}` AS valid_from, f.`{vu}` AS valid_until{emb_sel}
            """
        by_key: dict[str, ExistingFact] = {}
        with self._driver.session() as session:
            for row in session.run(q, keys=uniq):
                k = row["key"]
                if k in by_key:
                    continue
                emb = None
                if emb_prop:
                    raw = row.get("embedding")
                    if raw is not None:
                        emb = [float(x) for x in raw]
                by_key[k] = ExistingFact(
                    fact_id=row["id"],
                    key=k,
                    body=row["body"] or "",
                    valid_from=_parse_dt(row["valid_from"]),
                    valid_until=_parse_dt(row["valid_until"]),
                    embedding=emb,
                )
        return by_key

    def load_context_for_injection(
        self,
        proposal_key: str,
        cohort_keys: list[str],
        *,
        constraint_bounds: dict[str, float] | None = None,
    ) -> GraphContext:
        """
        Experiment C: proposal is usually the last write in `fact_keys`; cohort includes
        all keys written in that injection (semantic pair, temporal pair, etc.).
        """
        ctx = self.load_context_for_key(proposal_key, constraint_bounds=constraint_bounds)
        others = [k for k in dict.fromkeys(cohort_keys) if k != proposal_key]
        if not others:
            return ctx
        fetched = self.fetch_facts_by_keys(others)
        extra = [fetched[k] for k in others if k in fetched]
        return ctx.model_copy(update={"neighbor_facts": list(ctx.neighbor_facts) + extra})
