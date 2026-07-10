"""Deterministic local vectorizer for asset search."""

from __future__ import annotations

import hashlib
import math
import re


class AssetVectorizer:
    """Creates deterministic embeddings without external API dependency."""

    def __init__(self, dimension: int = 16) -> None:
        self.dimension = dimension

    def encode(self, text: str) -> list[float]:
        """Encode arbitrary text into a normalized fixed-size vector."""
        normalized = text.lower().strip()
        if not normalized:
            return [0.0] * self.dimension

        tokens = re.findall(r"[a-zа-я0-9_]+", normalized, flags=re.IGNORECASE)
        vector = [0.0] * self.dimension
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            for idx in range(self.dimension):
                value = digest[idx] / 255.0
                vector[idx] += value

        norm = math.sqrt(sum(x * x for x in vector))
        if norm == 0:
            return vector
        return [x / norm for x in vector]
