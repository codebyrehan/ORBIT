"""Durable local storage for ORBIT model metadata."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import cast
import json

from orbit.core.models import ModelCatalog, ModelModality, ModelSpec


class ModelStore:
    """Persist the runtime-neutral model catalog as a small JSON document."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> ModelCatalog:
        if not self.path.exists():
            return ModelCatalog()
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            raise TypeError("model catalog must contain a JSON array")
        catalog = ModelCatalog()
        for item in raw:
            if not isinstance(item, dict):
                raise TypeError("each model catalog entry must be an object")
            catalog.register(self._from_dict(item))
        return catalog

    def all(self) -> tuple[ModelSpec, ...]:
        return self.load().all()

    def get(self, model_id: str) -> ModelSpec | None:
        return self.load().get(model_id)

    def upsert(self, model: ModelSpec) -> None:
        catalog = self.load()
        catalog.register(model)
        self.save(catalog)

    def save(self, catalog: ModelCatalog) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload: list[dict[str, object]] = []
        for model in catalog.all():
            item = cast(dict[str, object], asdict(model))
            item["modality"] = model.modality.value
            for key in ("capabilities", "runtimes", "tags"):
                item[key] = sorted(cast(frozenset[str], item[key]))
            payload.append(item)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        temporary.replace(self.path)

    @staticmethod
    def _from_dict(item: dict[str, object]) -> ModelSpec:
        capabilities = item.get("capabilities", [])
        runtimes = item.get("runtimes", [])
        tags = item.get("tags", [])
        size_bytes_raw = item.get("size_bytes")
        min_memory_bytes_raw = item.get("min_memory_bytes")
        local_path_raw = item.get("local_path")
        size_bytes: int | None = size_bytes_raw if isinstance(size_bytes_raw, int) else None
        min_memory_bytes: int | None = (
            min_memory_bytes_raw if isinstance(min_memory_bytes_raw, int) else None
        )
        local_path: str | None = local_path_raw if isinstance(local_path_raw, str) else None
        return ModelSpec(
            model_id=str(item["model_id"]),
            display_name=str(item["display_name"]),
            modality=ModelModality(str(item.get("modality", "text"))),
            size_bytes=size_bytes,
            min_memory_bytes=min_memory_bytes,
            capabilities=frozenset(cast(list[str], capabilities)),
            runtimes=frozenset(cast(list[str], runtimes)),
            tags=frozenset(cast(list[str], tags)),
            local_path=local_path,
        )
