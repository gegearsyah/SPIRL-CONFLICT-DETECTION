#!/usr/bin/env python3
"""
Replay conflict_injected rows from a JSONL execution log through the modular
governance lab (Neo4j + kg_orchestrator).

Supports:
  * Legacy Paper 3 logs under ../research/ (e.g. paper3_execution_log.experiment_C.jsonl)
  * Real Data Lab logs under ../real-data-lab/research/ (real_data_lab_execution_log.jsonl)

RDL rows often list only the proposed key in result.fact_keys; baseline keys live in
based_on_facts and proposal key in proposed_fact_key — we merge those into the cohort
so neighbor_facts load correctly.

Reads:
  --research-dir / --log-name  → execution JSONL
  --basis-path (or research-dir / paper3_basis.skf.json) → optional SKF / basis bodies

Usage (from state-orchestration-lab/):
  pip install -r requirements.txt
  copy .env.example .env   # fill NEO4J_*

  python replay_governance_log.py --dry-run --limit 10
  python replay_governance_log.py --profile Full --limit 20

  # Real Data Lab (use project SKF for bodies when nodes omit text in basis):
  python replay_governance_log.py \\
    --research-dir ../real-data-lab/research \\
    --log-name real_data_lab_execution_log.jsonl \\
    --basis-path "../real-data-lab/Project Core Platform.skf.json" \\
    --profile Full --limit 5

Env:
  PAPER3_TEAM_CAP_BOUND, PAPER3_CROSS_ENCODER, PAPER3_LEGACY_SEMANTIC, NEO4J_*, etc.
  (see prior replay_experiment_c / README).

Ablation profiles: T, T_sem_high, T_sem_retrieval, T_sem_nli, Full (--all-profiles).
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

_LAB = Path(__file__).resolve().parent
load_dotenv(_LAB / ".env", override=False)
load_dotenv(_LAB / "spiral_semantic_stages" / ".env", override=False)

_DEFAULT_RESEARCH = _LAB.parent / "research"
_LOG_DEFAULT = "paper3_execution_log.experiment_C.jsonl"
_BASIS_NAME = "paper3_basis.skf.json"


def load_basis_map(path: Path) -> dict[str, dict]:
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    m: dict[str, dict] = {}
    for corp in data.get("corpora", []):
        for fact in corp.get("facts", []):
            k = fact.get("key")
            if k:
                m[k] = fact
    # Real Data Lab / standalone SKF: top-level "facts" with "value" text
    for fact in data.get("facts", []):
        k = fact.get("key")
        if not k or k in m:
            continue
        body = fact.get("body") or fact.get("value") or ""
        m[k] = {**fact, "body": body}
    return m


def iter_injections(log_path: Path):
    with log_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if row.get("action") != "conflict_injected":
                continue
            res = row.get("result") or {}
            if not res.get("success", True):
                continue
            keys = res.get("fact_keys") or []
            if (
                not keys
                and not (row.get("based_on_facts") or [])
                and not (row.get("proposed_fact_key") or "").strip()
            ):
                continue
            yield row, keys


def cohort_keys_for_replay(row: dict) -> list[str]:
    """
    Merge result.fact_keys with RDL based_on_facts so Neo4j can load cohort neighbors.
    Order: baseline keys first, then proposal keys (dedupe, stable).
    """
    res = row.get("result") or {}
    seen: set[str] = set()
    out: list[str] = []
    for k in row.get("based_on_facts") or []:
        if k and k not in seen:
            seen.add(k)
            out.append(k)
    for k in res.get("fact_keys") or []:
        if k and k not in seen:
            seen.add(k)
            out.append(k)
    pk = (row.get("proposed_fact_key") or "").strip()
    if pk and pk not in seen:
        out.append(pk)
    return out


def proposal_key_for_injection(gold: str, fact_keys: list[str]) -> str:
    if gold == "constraint_violation":
        for k in fact_keys:
            if "team_fact" in k:
                return k
    return fact_keys[-1]


def proposal_key_for_replay(row: dict, gold: str, cohort_keys: list[str]) -> str:
    pk = (row.get("proposed_fact_key") or "").strip()
    if pk:
        return pk
    if not cohort_keys:
        return ""
    return proposal_key_for_injection(gold, cohort_keys)


def constraint_bounds_for_row(gold: str, fact_keys: list[str]) -> dict[str, float]:
    if gold != "constraint_violation":
        return {}
    if not any("team_cap" in k for k in fact_keys):
        return {}
    cap = float(os.environ.get("PAPER3_TEAM_CAP_BOUND", "8"))
    return {"team_cap": cap}


def pick_proposal_fields(
    proposal_key: str,
    ctx,
    basis_map: dict[str, dict],
) -> tuple[str, datetime | None, datetime | None, list[float] | None]:
    same = [f for f in ctx.same_key_facts if f.key == proposal_key]
    best = max(same, key=lambda f: len(f.body or ""), default=None)
    if best and (best.body or "").strip():
        return (
            best.body,
            best.valid_from,
            best.valid_until,
            best.embedding,
        )
    b = basis_map.get(proposal_key, {})
    body = (
        (b.get("body") or b.get("value") or "").strip()
        or f"(no body in Neo4j or basis for {proposal_key})"
    )
    return body, None, None, None


def lab_classes_from_findings(findings: list) -> set[str]:
    out: set[str] = set()
    for f in findings:
        c = f.conflict_class
        if c == "ontology_violation":
            continue
        out.add(c)
    return out


def gold_vs_lab(gold: str, lab_classes: set[str]) -> str:
    if gold == "semantic_contradiction" and "semantic_contradiction" in lab_classes:
        return "match"
    if gold == "temporal_invalidation" and "temporal_invalidation" in lab_classes:
        return "match"
    if gold == "constraint_violation" and "constraint_violation" in lab_classes:
        return "match"
    if gold == "dependency_impact" and "dependency_impact" in lab_classes:
        return "match"
    if lab_classes:
        return "partial"
    return "miss"


def resolve_nli(
    *,
    use_oracle: bool,
    use_cross_encoder: bool,
):
    """Return (nli_fn | None, source_description)."""
    if use_oracle:

        class OracleNLI:
            def __init__(self) -> None:
                self._gold = ""

            def set_gold(self, g: str) -> None:
                self._gold = g

            def __call__(self, a: str, b: str) -> bool:
                return self._gold == "semantic_contradiction"

        return OracleNLI(), "oracle_per_row"

    try:
        from kg_orchestrator.engines.progressive_semantic import (
            progressive_semantic_stack_available,
        )

        if progressive_semantic_stack_available():
            return None, "progressive_pipeline"
    except ImportError:
        pass

    if use_cross_encoder:
        from kg_orchestrator.nli_cross_encoder import try_cross_encoder_nli

        fn = try_cross_encoder_nli()
        if fn is not None:
            return fn, "cross_encoder"
    return None, "none"


def run_one_profile(
    *,
    log_path: Path,
    basis_map: dict[str, dict],
    acc,
    profile: str,
    nli_holder,
    nli_source: str,
    limit: int,
) -> tuple[list[dict], dict]:
    from kg_orchestrator import FactProposal
    from kg_orchestrator.ablation_metrics import macro_prf1
    from kg_orchestrator.profiles import build_governance_orchestrator
    from kg_orchestrator.replay_embeddings import ensure_fact_embeddings

    needs_nli = profile in ("T_sem_nli", "Full")
    nli_fn = None
    if needs_nli:
        if nli_holder is None and nli_source != "progressive_pipeline":
            raise ValueError(
                f"Profile {profile} requires NLI or progressive stack; "
                "install requirements-eval.txt + requirements-spiral-stages.txt, "
                "or pass --nli-oracle"
            )
        nli_fn = nli_holder

    orch = build_governance_orchestrator(profile, nli_fn)

    async def _drive() -> tuple[list[dict], dict]:
        rows_out: list[dict] = []
        gold_list: list[str] = []
        pred_sets: list[set[str]] = []

        processed = 0
        for row, _raw_fact_keys in iter_injections(log_path):
            if limit and processed >= limit:
                break
            processed += 1

            gold = row.get("conflict_class", "")
            if (
                nli_source == "oracle_per_row"
                and nli_holder is not None
                and hasattr(nli_holder, "set_gold")
            ):
                nli_holder.set_gold(gold)

            keys = cohort_keys_for_replay(row)
            proposal_key = proposal_key_for_replay(row, gold, keys)
            if not proposal_key:
                continue
            bounds = constraint_bounds_for_row(gold, keys)
            ctx = acc.load_context_for_injection(
                proposal_key, keys, constraint_bounds=bounds
            )
            body, vf, vu, emb = pick_proposal_fields(proposal_key, ctx, basis_map)

            md: dict = {"governance_replay_injection": row.get("injection_number")}
            if gold == "semantic_contradiction":
                md["governance_replay_relax_stage1_semantic"] = True
                md["paper3_relax_stage1_for_semantic_replay"] = True

            proposal = FactProposal(
                key=proposal_key,
                body=body,
                valid_from=vf or datetime.now(timezone.utc),
                valid_until=vu,
                embedding=emb,
                metadata=md,
            )
            hydrate = profile in ("Full", "T_sem_nli") and gold == "semantic_contradiction"
            proposal, ctx = ensure_fact_embeddings(proposal, ctx, enabled=hydrate)
            findings = await orch.evaluate_async(proposal, ctx)
            lab_cls = lab_classes_from_findings(findings)
            agree = gold_vs_lab(gold, lab_cls)
            log_detected = (row.get("result") or {}).get("async_observed", {}).get(
                "detected"
            )

            gold_list.append(gold)
            pred_sets.append(set(lab_cls))

            rows_out.append(
                {
                    "profile": profile,
                    "injection_number": row.get("injection_number"),
                    "gold_class": gold,
                    "proposal_key": proposal_key,
                    "cohort_keys": ";".join(keys),
                    "neo4j_same_key_count": len(ctx.same_key_facts),
                    "neo4j_neighbor_count": len(ctx.neighbor_facts),
                    "neo4j_inbound_deps": len(ctx.inbound_dependency_sources),
                    "lab_classes": ";".join(sorted(lab_cls)),
                    "lab_findings_n": len(findings),
                    "coarse_agreement": agree,
                    "log_async_detected": log_detected,
                }
            )

        metrics = macro_prf1(gold_list, pred_sets)
        metrics["profile"] = profile
        metrics["nli_source"] = nli_source
        metrics["rows"] = len(rows_out)
        return rows_out, metrics

    return asyncio.run(_drive())


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Replay conflict_injected JSONL (Paper 3 or Real Data Lab) via governance lab + Neo4j"
    )
    ap.add_argument(
        "--research-dir",
        type=Path,
        default=_DEFAULT_RESEARCH,
        help="Folder containing execution JSONL",
    )
    ap.add_argument(
        "--log-name",
        default=_LOG_DEFAULT,
        help="JSONL file under research-dir (e.g. real_data_lab_execution_log.jsonl)",
    )
    ap.add_argument(
        "--basis-path",
        type=Path,
        default=None,
        help="SKF / basis JSON for bodies (default: <research-dir>/paper3_basis.skf.json). "
        "For RDL use ../real-data-lab/Project Core Platform.skf.json",
    )
    ap.add_argument("--limit", type=int, default=0, help="Max injections (0 = all)")
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse log + basis only; do not connect to Neo4j",
    )
    ap.add_argument(
        "--csv",
        type=Path,
        default=None,
        help="Write CSV summary for single-profile run",
    )
    ap.add_argument(
        "--profile",
        default="Full",
        help="Governance profile: T | T_sem_high | T_sem_retrieval | T_sem_nli | Full",
    )
    ap.add_argument(
        "--all-profiles",
        action="store_true",
        help="Run all profiles; write per-profile CSV + results/paper3_ablation_summary.json",
    )
    ap.add_argument(
        "--nli-oracle",
        action="store_true",
        help="Use gold-label oracle for NLI (smoke tests only; inflates semantic scores)",
    )
    ap.add_argument(
        "--no-cross-encoder",
        action="store_true",
        help="Do not try to load sentence-transformers CrossEncoder",
    )
    ap.add_argument(
        "--metrics-json",
        type=Path,
        default=None,
        help="Write macro metrics JSON for single-profile run",
    )
    ap.add_argument(
        "--summary-json",
        type=Path,
        default=None,
        help="With --all-profiles, write aggregated summary here (default: results/paper3_ablation_summary.json)",
    )
    args = ap.parse_args()

    if args.nli_oracle:
        os.environ["PAPER3_LEGACY_SEMANTIC"] = "1"

    log_path = args.research_dir / args.log_name
    basis_path = args.basis_path or (args.research_dir / _BASIS_NAME)

    if not log_path.is_file():
        print(f"Missing log: {log_path}", file=sys.stderr)
        return 1

    if not basis_path.is_file():
        print(
            f"Missing basis SKF: {basis_path}\n"
            f"Hint: for Real Data Lab pass e.g.\n"
            f'  --basis-path "../real-data-lab/Project Core Platform.skf.json"',
            file=sys.stderr,
        )
        return 1

    basis_map = load_basis_map(basis_path)
    print(f"Basis keys loaded: {len(basis_map)} from {basis_path.name}")
    print(f"Log: {log_path}")

    if args.dry_run:
        processed = 0
        for row, _ in iter_injections(log_path):
            if args.limit and processed >= args.limit:
                break
            processed += 1
            gold = row.get("conflict_class", "")
            cohort = cohort_keys_for_replay(row)
            pk = proposal_key_for_replay(row, gold, cohort)
            print(
                f"  #{row.get('injection_number')} {gold} proposal_key={pk} cohort={cohort}"
            )
        print(f"Dry run: {processed} injections parsed.")
        return 0

    try:
        from kg_orchestrator.neo4j_io import Neo4jGraphAccessor
    except ImportError as e:
        print(e, file=sys.stderr)
        return 1

    try:
        acc = Neo4jGraphAccessor()
    except Exception as e:
        print(f"Neo4j: {e}", file=sys.stderr)
        return 1

    limit = args.limit or 0
    results_dir = _LAB / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    nli_fn, nli_src = resolve_nli(
        use_oracle=args.nli_oracle,
        use_cross_encoder=not args.no_cross_encoder,
    )
    nli_holder = nli_fn
    if nli_src == "none" and (
        args.all_profiles
        or args.profile in ("T_sem_nli", "Full")
    ):
        print(
            "NLI/progressive stack unavailable: use --nli-oracle, or "
            "pip install -r requirements-eval.txt -r requirements-spiral-stages.txt",
            file=sys.stderr,
        )
        acc.close()
        return 1

    try:
        if args.all_profiles:
            from kg_orchestrator.profiles import PROFILE_NAMES

            all_metrics: list[dict] = []
            all_rows: list[dict] = []
            for prof in PROFILE_NAMES:
                rows_out, m = run_one_profile(
                    log_path=log_path,
                    basis_map=basis_map,
                    acc=acc,
                    profile=prof,
                    nli_holder=nli_holder,
                    nli_source=nli_src,
                    limit=limit,
                )
                for r in rows_out:
                    all_rows.append(r)
                m_compact = {
                    "profile": m["profile"],
                    "nli_source": m["nli_source"],
                    "rows": m["rows"],
                    "macro_precision": m["macro_precision"],
                    "macro_recall": m["macro_recall"],
                    "macro_f1": m["macro_f1"],
                }
                all_metrics.append(m_compact)
                csv_path = results_dir / f"paper3_ablation_{prof}.csv"
                if rows_out:
                    with csv_path.open("w", newline="", encoding="utf-8") as f:
                        w = csv.DictWriter(f, fieldnames=list(rows_out[0].keys()))
                        w.writeheader()
                        w.writerows(rows_out)
                    print(f"Wrote {csv_path}")
            summary_path = args.summary_json or (results_dir / "paper3_ablation_summary.json")
            payload = {
                "log": str(log_path),
                "basis": str(basis_path),
                "nli_source": nli_src,
                "limit": limit,
                "profiles": all_metrics,
            }
            summary_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            print(f"Wrote {summary_path}")
        else:
            rows_out, m = run_one_profile(
                log_path=log_path,
                basis_map=basis_map,
                acc=acc,
                profile=args.profile,
                nli_holder=nli_holder,
                nli_source=nli_src,
                limit=limit,
            )
            match = sum(1 for r in rows_out if r["coarse_agreement"] == "match")
            partial = sum(1 for r in rows_out if r["coarse_agreement"] == "partial")
            miss = sum(1 for r in rows_out if r["coarse_agreement"] == "miss")
            print(
                f"\nProfile={args.profile} nli={nli_src} processed={len(rows_out)} "
                f"coarse match={match} partial={partial} miss={miss}\n"
                f"macro P/R/F1 = {m['macro_precision']:.4f} / {m['macro_recall']:.4f} / {m['macro_f1']:.4f}"
            )
            if args.csv:
                args.csv.parent.mkdir(parents=True, exist_ok=True)
                with args.csv.open("w", newline="", encoding="utf-8") as f:
                    w = csv.DictWriter(
                        f, fieldnames=list(rows_out[0].keys()) if rows_out else []
                    )
                    if rows_out:
                        w.writeheader()
                        w.writerows(rows_out)
                print(f"Wrote {args.csv}")
            if args.metrics_json:
                args.metrics_json.parent.mkdir(parents=True, exist_ok=True)
                out_m = {k: v for k, v in m.items() if k != "per_class"}
                out_m["per_class"] = m["per_class"]
                args.metrics_json.write_text(
                    json.dumps(out_m, indent=2), encoding="utf-8"
                )
                print(f"Wrote {args.metrics_json}")
    finally:
        acc.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
