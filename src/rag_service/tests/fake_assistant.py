"""An Assistant over the real corpus whose similarity scores the test chooses.

Every query embeds to the same vector q = (1, 0), and each section's vector is (s, sqrt(1 - s²)),
so the dot product (the retrieval score) of a section is exactly the s given for it. Version
selection, retrieval and response building run unchanged; only the model is replaced.
"""

import math
import threading
import time
from datetime import UTC, datetime

import numpy as np

from app.documents import load_corpus
from app.index_store import Index
from app.service import Assistant
from app.settings import Settings, load_settings
from tests.corpus_files import KNOWLEDGE_DIR

CORPUS = load_corpus(KNOWLEDGE_DIR)
CHUNKS = {chunk.chunk_id: chunk for doc in CORPUS for chunk in doc.chunks}
# 2026-10-04 12:00 in Istanbul.
FIXED_NOW = datetime(2026, 10, 4, 9, 0, tzinfo=UTC)


class QueryEmbedder:
    """Stands in for the model at query time; records how and where it was called."""

    model_id = "fake-query@rev1"
    dimension = 2

    def __init__(self, max_tokens: int = 512, delay_seconds: float = 0.0):
        self.max_tokens = max_tokens
        self.delay_seconds = delay_seconds
        self.embedded_texts: list[str] = []
        self.threads: set[threading.Thread] = set()
        self.max_concurrent_calls = 0
        self._running = 0
        self._lock = threading.Lock()

    def count_tokens(self, text: str) -> int:
        return len(text.split()) + 2  # like <s> and </s>

    def embed(self, texts: list[str]) -> np.ndarray:
        with self._lock:
            self._running += 1
            self.max_concurrent_calls = max(self.max_concurrent_calls, self._running)
            self.threads.add(threading.current_thread())
            self.embedded_texts.extend(texts)
        time.sleep(self.delay_seconds)
        with self._lock:
            self._running -= 1
        return np.array([[1.0, 0.0]] * len(texts), dtype=np.float32)


def index_with_scores(scores: dict[str, float]) -> Index:
    """Every real section; sections not listed score 0 and are ordered by chunk_id among equals."""
    unknown = set(scores) - set(CHUNKS)
    assert not unknown, f"not real sections: {unknown}"
    chunks = tuple(CHUNKS.values())
    vectors = np.array(
        [[s, math.sqrt(1 - s * s)] for s in (scores.get(c.chunk_id, 0.0) for c in chunks)],
        dtype=np.float32,
    )
    return Index(fingerprint="test-fingerprint", chunks=chunks, vectors=vectors)


def make_assistant(
    scores: dict[str, float] | None = None,
    settings: Settings | None = None,
    embedder: QueryEmbedder | None = None,
    now: datetime = FIXED_NOW,
) -> Assistant:
    return Assistant(
        settings=settings or load_settings({}),
        documents=CORPUS,
        embedder=embedder or QueryEmbedder(),
        index=index_with_scores(scores or {}),
        clock=lambda: now,
    )
