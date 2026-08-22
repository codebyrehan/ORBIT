"""Durable local storage for ORBIT model metadata."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

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
            raise ValueError("model catalog must contain a JSON array")
        catalog = ModelCatalog()
        for item in raw:
            if not isinstance(item, dict):
                raise ValueError("each model catalog entry must be an object")
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
        payload = []
        for model in catalog.all():
            item = asdict(model)
            item["modality"] = model.modality.value
            for key in ("capabilities", "runtimes", "tags"):
                item[key] = sorted(item[key])
            payload.append(item)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        temporary.replace(self.path)

    @staticmethod
    def _from_dict(item: dict[str, object]) -> ModelSpec:
        return ModelSpec(
            model_id=str(item["model_id"]),
            display_name=str(item["display_name"]),
            modality=ModelModality(str(item.get("modality", "text"))),
            size_bytes=item.get("size_bytes") if isinstance(item.get("size_bytes"), int) else None,
            min_memory_bytes=item.get("min_memory_bytes") if isinstance(item.get("min_memory_bytes"), int) else None,
            capabilities=frozenset(item.get("capabilities", [])),
            runtimes=frozenset(item.get("runtimes", [])),
            tags=frozenset(item.get("tags", [])),
            local_path=item.get("local_path") if isinstance(item.get("local_path"), str) else None,
        )
