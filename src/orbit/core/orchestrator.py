"""Inference orchestration across models, scheduling, runtime adapters, and failover."""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass

from orbit.core.failover import RuntimeFailover
from orbit.core.load_control import RuntimeLoadController
from orbit.core.models import ModelSpec
from orbit.core.runtime import GenerationRequest, RuntimeAdapter
from orbit.core.runtime_manager import RuntimeManager
from orbit.core.scheduler import Placement, ResourceScheduler


@dataclass(frozen=True, slots=True)
class ExecutionPlan:
    """Validated model/runtime placement ready for execution."""

    model: ModelSpec
    runtime: RuntimeAdapter
    placement: Placement


class InferenceOrchestrator:
    """Turn a model request into a validated, runtime-backed generation stream."""

    def __init__(self, scheduler: ResourceScheduler, runtimes: RuntimeManager, failover: RuntimeFailover | None = None, load_control: RuntimeLoadController | None = None) -> None:
        self.scheduler = scheduler
        self.runtimes = runtimes
        self.failover = failover or RuntimeFailover(runtimes)
        self.load_control = load_control or RuntimeLoadController()

    async def plan(self, model: ModelSpec, runtime_name: str | None = None) -> ExecutionPlan:
        candidates: tuple[str, ...]
        if runtime_name:
            candidates = (runtime_name,)
        elif model.runtimes:
            candidates = tuple(sorted(model.runtimes))
        else:
            candidates = self.runtimes.names()

        plans: list[ExecutionPlan] = []
        for name in candidates:
            adapter = self.runtimes.get(name)
            if adapter is None:
                continue
            placement = self.scheduler.place(model, name)
            if placement is None:
                continue
            status = self.runtimes.health_status(name)
            if status is not None and not status.healthy:
                continue
            if not await adapter.health():
                continue
            plans.append(ExecutionPlan(model=model, runtime=adapter, placement=placement))

        if not plans:
            raise RuntimeError(f"no healthy compatible runtime available for model: {model.model_id}")

        scored: list[tuple[ExecutionPlan, int]] = []
        for plan in plans:
            snapshot = await self.load_control.snapshot(plan.runtime.info.name)
            scored.append((plan, snapshot.available))
        selected = max(scored, key=lambda item: (item[0].placement.score, item[1], item[0].runtime.info.name))[0]
        self.runtimes.select(selected.runtime.info.name)
        return selected

    async def generate(
        self,
        model: ModelSpec,
        prompt: str,
        *,
        runtime_name: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        capacity_timeout: float | None = None,
    ) -> AsyncIterator[str]:
        plan = await self.plan(model, runtime_name)
        request = GenerationRequest(prompt=prompt, model=model.model_id, temperature=temperature, max_tokens=max_tokens)
        candidates = tuple(sorted(model.runtimes)) if model.runtimes else self.runtimes.names()
        attempted = {plan.runtime.info.name}

        while True:
            emitted = False
            acquired_runtime: str | None = None
            try:
                runtime_to_acquire = plan.runtime.info.name
                await self.load_control.acquire(runtime_to_acquire, timeout=capacity_timeout)
                acquired_runtime = runtime_to_acquire
                async for token in plan.runtime.generate(request):
                    emitted = True
                    yield token
                return
            except Exception:
                if emitted:
                    raise
                decision = await self.failover.recover(plan.runtime.info.name, candidates)
                if decision is None or decision.runtime_name in attempted:
                    raise
                attempted.add(decision.runtime_name)
                plan = await self.plan(model, decision.runtime_name)
            finally:
                if acquired_runtime is not None:
                    await self.load_control.release(acquired_runtime)
