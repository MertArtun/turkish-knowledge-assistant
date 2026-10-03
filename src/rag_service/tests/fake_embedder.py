"""Deterministic stand-in for the local embedding model in default (offline) tests.

It is a test tool only; the service has no fake or mock embedding mode.
"""

import hashlib

import numpy as np


class FakeEmbedder:
    def __init__(
        self,
        model_id: str = "fake-e5@rev1",
        dimension: int = 8,
        max_tokens: int = 512,
        poison: str | None = None,
    ):
        self.model_id = model_id
        self.dimension = dimension
        self.max_tokens = max_tokens
        # "nan", "zero" or "short" makes embed() return an invalid first vector.
        self.poison = poison
        self.counted_texts: list[str] = []
        self.embedded_texts: list[str] = []

    def count_tokens(self, text: str) -> int:
        self.counted_texts.append(text)
        return len(text.split()) + 2  # like <s> and </s>

    def embed(self, texts: list[str]) -> np.ndarray:
        self.embedded_texts.extend(texts)
        vectors = np.array([self._vector(text) for text in texts], dtype=np.float32)
        if self.poison == "nan":
            vectors[0, 0] = np.nan
        elif self.poison == "zero":
            vectors[0] = 0.0
        elif self.poison == "short":
            vectors = vectors[:, :-1]
        return vectors

    def _vector(self, text: str) -> np.ndarray:
        digest = hashlib.sha256(f"{self.model_id}|{text}".encode()).digest()
        raw = np.frombuffer(digest[: self.dimension], dtype=np.uint8).astype(np.float32) - 127.5
        return raw / np.linalg.norm(raw)
