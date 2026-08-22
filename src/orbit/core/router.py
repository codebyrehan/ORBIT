"""Deterministic request routing over models and healthy runtime adapters."""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass

from orbit.core.models import ModelCatalog, ModelSpec
from orbit.core.orchestrator import ExecutionPlan, InferenceOrchestrator


@dataclass(frozen=True, slots=True)
class RouteRequest:
    model_id: str
    runtime_name: str | None = None


@dataclass(frozen=True, slots=True)
class RouteDecision:
    request: RouteRequest
    plan: ExecutionPlan

    @property
    def model_id(self) -> str:
        return self.plan.model.model_id

    @property
    def runtime_name(self) -> str:
        return self.plan.runtime.info.name

    @property
    def score(self) -> float:
        return self.plan.placement.score

    @property
    def reason(self) -> str:
        return self.plan.placement.reason


class InferenceRouter:
    """Resolve a request to a model and a healthy, resource-compatible runtime."""

    def __init__(self, catalog: ModelCatalog, orchestrator: InferenceOrchestrator) -> None:
        self.catalog = catalog
        self.orchestrator = orchestrator

    async def route(self, request: RouteRequest) -> RouteDecision:
        model = self.catalog.get(request.model_id)
        if model is None:
            raise LookupError(f"unknown model: {request.model_id}")
        try:
            plan = await self.orchestrator.plan(model, request.runtime_name)
        except RuntimeError as exc:
            raise RuntimeError(f"unable to route model {request.model_id}: {exc}") from exc
        return RouteDecision(request=request, plan=plan)

    async def generate(
        self,
        request: RouteRequest,
        prompt: str,
        *,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        decision = await self.route(request)
        async for chunk in self.orchestrator.generate(
            decision.plan.model,
            prompt,
            runtime_name=decision.runtime_name,
            temperature=temperature,
            max_tokens=max_tokens,
        ):
            yield chunk
