"""Runtime abstraction used by ORBIT's model layer."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import AsyncIterator


@dataclass(frozen=True, slots=True)
class GenerationRequest:
    prompt: str
    model: str
    temperature: float = 0.7
    max_tokens: int | None = None


@dataclass(frozen=True, slots=True)
class RuntimeInfo:
    name: str
    version: str
    capabilities: frozenset[str]


class RuntimeAdapter(ABC):
    """Stable interface between ORBIT and an inference backend."""

    @property
    @abstractmethod
    def info(self) -> RuntimeInfo:
        raise NotImplementedError

    @abstractmethod
    async def health(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def generate(self, request: GenerationRequest) -> AsyncIterator[str]:
        raise NotImplementedError
