"""Exact similarity search inside the version and scope view of one request.

Rows are restricted to the selected document versions BEFORE scoring and top-k, so an expired,
future, draft or out-of-scope section can never take a top-k slot, whatever its score.
"""

from collections.abc import Mapping
from dataclasses import dataclass

import numpy as np

from app.contracts import VersionDecision
from app.documents import Chunk
from app.index_store import Index


@dataclass(frozen=True)
class ScoredChunk:
    chunk: Chunk
    # Cosine similarity, for logs and measurement only; it is not a confidence and is never
    # returned in an answer.
    score: float


def retrieve(
    index: Index,
    query_vector: np.ndarray,
    decisions: Mapping[str, VersionDecision],
    top_k: int,
    min_score: float | None = None,
) -> list[ScoredChunk]:
    """Top-k sections of the selected versions by dot product; equal scores ordered by chunk_id."""
    searchable_docs = {
        decision.selected.doc_id for decision in decisions.values() if decision.selected
    }
    rows = [row for row, chunk in enumerate(index.chunks) if chunk.doc_id in searchable_docs]
    scores = index.vectors[rows] @ query_vector
    results = [
        ScoredChunk(index.chunks[row], score)
        for row, score in zip(rows, scores.tolist(), strict=True)
    ]
    results.sort(key=lambda result: (-result.score, result.chunk.chunk_id))
    if min_score is not None:
        results = [result for result in results if result.score >= min_score]
    return results[:top_k]
