"""Fan-out proposals to engines; merge findings — the 'state orchestration' seam."""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Sequence

from kg_orchestrator.models import FactProposal, GovernanceFinding, GraphContext


class GovernanceOrchestrator:
    def __init__(self, engines: Sequence[object]) -> None:
        self._engines = list(engines)

    def evaluate_sync(
        self, proposal: FactProposal, ctx: GraphContext
    ) -> list[GovernanceFinding]:
        out: list[GovernanceFinding] = []
        for eng in self._engines:
            out.extend(eng.evaluate(proposal, ctx))  # type: ignore[union-attr]
        return out

    async def evaluate_async(
        self, proposal: FactProposal, ctx: GraphContext
    ) -> list[GovernanceFinding]:
        """Run engines concurrently (CPU-bound NLI / SparseCL release the GIL in native code)."""

        loop = asyncio.get_running_loop()

        def run_one(eng: object) -> list[GovernanceFinding]:
            return eng.evaluate(proposal, ctx)  # type: ignore[union-attr]

        with ThreadPoolExecutor(max_workers=len(self._engines) or 1) as pool:
            tasks = [
                loop.run_in_executor(pool, run_one, eng) for eng in self._engines
            ]
            parts = await asyncio.gather(*tasks)
        merged: list[GovernanceFinding] = []
        for p in parts:
            merged.extend(p)
        return merged
