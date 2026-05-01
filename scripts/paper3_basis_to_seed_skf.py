"""
Emit one Spirl-style seed SKF per Paper 3 corpus from research/paper3_basis.skf.json.

Output shape matches research/paper3_seed_api_service.skf.json (skf_version 1.2).
Excludes research.p3.* Phase-1 metadata facts and any edges touching those keys.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from paper3_paths import btc_root

ROOT = btc_root()
BASIS_PATH = ROOT / "research" / "paper3_basis.skf.json"
OUT_DIR = ROOT / "research"

# slug -> output filename stem (after paper3_seed_)
SEED_NAMES = {
    "paper3_data_pipeline": "data_pipeline",
    "paper3_saas": "saas",
    "paper3_api_service": "api_service",
}

PROJECT_BLOCK: dict[str, dict] = {
    "paper3_data_pipeline": {
        "name": "Research — Data Pipeline Platform",
        "description": "Synthetic batch/stream data platform base corpus for Paper 3 (from basis export).",
        "slug": "research-data-pipeline",
        "tags": ["research", "paper3", "data-pipeline"],
    },
    "paper3_saas": {
        "name": "Research — SaaS Analytics Platform",
        "description": "Synthetic multi-tenant analytics product base corpus for Paper 3 (from basis export).",
        "slug": "research-saas-analytics",
        "tags": ["research", "paper3", "saas"],
    },
    "paper3_api_service": {
        "name": "Research — Core API Service",
        "description": "Synthetic API gateway + microservices base corpus for Paper 3 (from basis export).",
        "slug": "research-api-service",
        "tags": ["research", "paper3", "api"],
    },
}


def _iso_z() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _is_meta_key(key: str) -> bool:
    return key.startswith("research.p3.")


def basis_fact_to_seed(f: dict) -> dict:
    return {
        "key": f["key"],
        "layer": "product",
        "category": f["kind"],
        "value": f["body"],
        "confidence": 0.9,
        "references": [],
        "metadata": {},
        "valid_from": "2026-01-01T00:00:00Z",
        "valid_until": None,
    }


def basis_edge_to_seed(e: dict) -> dict:
    return {
        "from": e["source_fact_key"],
        "to": e["target_fact_key"],
        "type": e["edge_type"],
        "description": "",
    }


def corpus_to_seed_doc(
    corpus: dict,
    *,
    exported_at: str,
    basis_exported_at: str | None,
    experiment_id: str,
) -> dict:
    slug = corpus["slug"]
    facts_in = corpus.get("facts") or []
    edges_in = corpus.get("edges") or []

    seed_facts = [basis_fact_to_seed(f) for f in facts_in if not _is_meta_key(str(f.get("key") or ""))]
    kept = {f["key"] for f in seed_facts}

    seed_edges = []
    for e in edges_in:
        a = str(e.get("source_fact_key") or "")
        b = str(e.get("target_fact_key") or "")
        if _is_meta_key(a) or _is_meta_key(b):
            continue
        if a not in kept or b not in kept:
            continue
        seed_edges.append(basis_edge_to_seed(e))

    proj = PROJECT_BLOCK[slug]
    label = slug.replace("paper3_", "").replace("_", " ")
    return {
        "skf_version": "1.2",
        "exported_at": exported_at,
        "source": {
            "agent": "paper3-basis-to-seed",
            "basis_exported_at": basis_exported_at,
            "basis_corpus_slug": slug,
            "paper3_experiment_id": experiment_id,
        },
        "project": proj,
        "facts": seed_facts,
        "edges": seed_edges,
        "episodes": [
            {
                "type": "extraction",
                "actor": "paper3-basis-to-seed",
                "content": f"Paper 3 {label} seed generated from paper3_basis.skf.json",
                "timestamp": exported_at,
            }
        ],
        "rules": [],
    }


def main() -> None:
    raw = json.loads(BASIS_PATH.read_text(encoding="utf-8"))
    corpora = raw.get("corpora") or []
    basis_exported = raw.get("exported_at")
    # Tag seed exports for the active experiment (C); basis snapshot may still say B.
    experiment_id = "C"

    exported_at = _iso_z()

    for c in corpora:
        slug = c.get("slug")
        if slug not in SEED_NAMES:
            continue
        doc = corpus_to_seed_doc(
            c,
            exported_at=exported_at,
            basis_exported_at=basis_exported,
            experiment_id=experiment_id,
        )
        name = SEED_NAMES[slug]
        out = OUT_DIR / f"paper3_seed_{name}.skf.json"
        out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"Wrote {out.relative_to(ROOT)} ({len(doc['facts'])} facts, {len(doc['edges'])} edges)")


if __name__ == "__main__":
    main()
