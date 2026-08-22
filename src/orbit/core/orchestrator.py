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
        candidates = (runtime_name,) if runtime_name else tuple(model.runtimes)
        if not candidates:
            candidates = self.runtimes.names()
        for name in candidates:
            adapter = self.runtimes.get(name)
            if adapter is None:
                continue
            placement = self.scheduler.place(model, name)
            if placement is None:
                continue
            if not await adapter.health():
                continue
            self.runtimes.select(name)
            return ExecutionPlan(model=model, runtime=adapter, placement=placement)
        raise RuntimeError(f"no healthy compatible runtime available for model: {model.model_id}")

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
