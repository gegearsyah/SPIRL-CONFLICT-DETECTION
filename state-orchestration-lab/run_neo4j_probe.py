#!/usr/bin/env python3
"""
Step 1 after installing: verify Aura (or any Neo4j) credentials and discover schema.

Usage (from Beyond Temporal Contradiction/state-orchestration-lab/):
  python run_neo4j_probe.py

Loads .env from this folder automatically.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load .env from script directory
_ROOT = Path(__file__).resolve().parent
load_dotenv(_ROOT / ".env")


def main() -> int:
    try:
        from neo4j import GraphDatabase
    except ImportError:
        print("Install deps: pip install -r requirements.txt", file=sys.stderr)
        return 1

    uri = os.environ.get("NEO4J_URI", "").strip()
    user = os.environ.get("NEO4J_USER", "neo4j").strip()
    password = os.environ.get("NEO4J_PASSWORD", "").strip()

    if not uri or not password:
        print("Missing NEO4J_URI or NEO4J_PASSWORD in .env", file=sys.stderr)
        return 1

    print(f"Connecting to {uri!s} as {user!r} ...")
    driver = GraphDatabase.driver(uri, auth=(user, password))
    try:
        driver.verify_connectivity()
        print("OK: connectivity verified.\n")
    except Exception as e:
        print(f"FAILED: {e}", file=sys.stderr)
        return 1

    with driver.session() as session:
        v = session.run("CALL dbms.components() YIELD name, versions, edition RETURN name, versions[0] AS version, edition").single()
        if v:
            print(f"Server: {v['name']} {v['version']} ({v['edition']})")

        rows = session.run("CALL db.labels() YIELD label RETURN label ORDER BY label").data()
        labels = [r["label"] for r in rows]
        print(f"\nLabels in database ({len(labels)}):")
        for lb in labels:
            c = session.run(f"MATCH (n:`{lb}`) RETURN count(n) AS c").single()
            n = c["c"] if c else 0
            print(f"  - {lb}: {n} nodes")

        # Hint: sample property keys for labels that look fact-like
        interesting = [lb for lb in labels if "fact" in lb.lower() or "Fact" in lb][:5]
        if not interesting and labels:
            interesting = labels[:3]
        for lb in interesting:
            rec = session.run(f"MATCH (n:`{lb}`) RETURN n LIMIT 1").single()
            if rec and rec["n"]:
                keys = sorted(rec["n"].keys())
                print(f"\nSample property keys on :{lb}: {keys}")

    driver.close()

    print(
        """
Next steps:
1) If your fact nodes are NOT label "Fact" or key field is not "key", set in .env:
     NEO4J_FACT_LABEL=YourLabel
     NEO4J_KEY_PROPERTY=epistemic_key
     NEO4J_BODY_PROPERTY=body
     NEO4J_VALID_FROM_PROPERTY=valid_from
     NEO4J_VALID_UNTIL_PROPERTY=valid_until
     NEO4J_INBOUND_REL_TYPES=DEPENDS_ON,USES

2) Run governance dry-run against a real key:
     python run_aura_governance.py --key your.fact.key

3) If step 2 finds 0 same-key rows, your label/property names still need tuning (use output above).
"""
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
