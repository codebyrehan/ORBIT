"""Embedding primitives for ORBIT semantic retrieval.

The interface deliberately stays provider-neutral. A deterministic hashing
fallback keeps local/offline installations functional while remote providers
can be plugged in without changing the retrieval API.
"""
from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass

_TOKEN_RE = re.compile(r"[\w'-]+", re.UNICODE)


@dataclass(frozen=True, slots=True)
class EmbeddingConfig:
    dimensions: int = 384


def tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def embed(text: str, dimensions: int = 384) -> list[float]:
    """Create a deterministic normalized feature vector without network calls."""
    if dimensions < 32:
        raise ValueError("embedding dimensions must be >= 32")
    vector = [0.0] * dimensions
    tokens = tokenize(text)
    if not tokens:
        return vector
    for token in tokens:
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=16).digest()
        index = int.from_bytes(digest[:8], "big") % dimensions
        sign = 1.0 if digest[8] & 1 else -1.0
        vector[index] += sign
        index2 = int.from_bytes(digest[9:16], "big") % dimensions
        vector[index2] += sign * 0.5
    norm = math.sqrt(sum(value * value for value in vector))
    if norm:
        vector = [value / norm for value in vector]
    return vector


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        raise ValueError("embedding dimensions do not match")
    return sum(a * b for a, b in zip(left, right, strict=True))
