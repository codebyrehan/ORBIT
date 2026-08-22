"""Inference orchestration across models, scheduling, and runtime adapters."""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass

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

    def __init__(self, scheduler: ResourceScheduler, runtimes: RuntimeManager) -> None:
        self.scheduler = scheduler
        self.runtimes = runtimes

    async def plan(self, model: ModelSpec, runtime_name: str | None = None) -> ExecutionPlan:
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
            if not await adapter.health():
                continue
            plans.append(ExecutionPlan(model=model, runtime=adapter, placement=placement))

        if not plans:
            raise RuntimeError(f"no healthy compatible runtime available for model: {model.model_id}")

        selected = max(plans, key=lambda plan: (plan.placement.score, plan.runtime.info.name))
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
    ) -> AsyncIterator[str]:
        plan = await self.plan(model, runtime_name)
        request = GenerationRequest(
            prompt=prompt,
            model=model.model_id,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        async for token in plan.runtime.generate(request):
            yield token
