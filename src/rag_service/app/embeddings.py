"""Local sentence embeddings with intfloat/multilingual-e5-small on CPU.

The model runs through ONNX Runtime from the ONNX export published in the model's own repository,
at a pinned commit. E5 expects "query: " / "passage: " prefixes, mean pooling over real tokens and
L2-normalised vectors, so a dot product between two vectors is their cosine similarity.
"""

from collections.abc import Sequence
from pathlib import Path
from typing import Protocol

import numpy as np
import onnxruntime
from huggingface_hub import hf_hub_download
from tokenizers import Tokenizer

from app.documents import Chunk, CorpusError

QUERY_PREFIX = "query: "
PASSAGE_PREFIX = "passage: "
# multilingual-e5-small has 512 position embeddings; a longer input fails inside the model
# (checked against the real model file in tests/test_embeddings_model.py).
E5_MAX_TOKENS = 512
BATCH_SIZE = 16


class EmbeddingError(Exception):
    """The embedding model could not be loaded or produced an unusable vector."""


class Embedder(Protocol):
    """What the index and retrieval need from a model. Exists so tests can use a fake."""

    model_id: str  # name and revision; part of the index fingerprint
    dimension: int
    max_tokens: int

    def count_tokens(self, text: str) -> int: ...

    def embed(self, texts: Sequence[str]) -> np.ndarray:
        """Returns float32 unit vectors, one row per text."""
        ...


def passage_text(chunk: Chunk) -> str:
    # The heading path goes into the embedding so that short sections keep their topic.
    return f"{PASSAGE_PREFIX}{' > '.join(chunk.heading_path)}\n{chunk.content}"


def query_text(question: str) -> str:
    return f"{QUERY_PREFIX}{question}"


def embed_query(embedder: Embedder, question: str) -> np.ndarray:
    return embedder.embed([query_text(question)])[0]


def check_passage_lengths(chunks: Sequence[Chunk], embedder: Embedder) -> None:
    """A section longer than the model input is a corpus error; it is never truncated."""
    for chunk in chunks:
        count = embedder.count_tokens(passage_text(chunk))
        if count > embedder.max_tokens:
            raise CorpusError(
                f"{chunk.chunk_id}: {count} tokens (prefix, heading path and special tokens "
                f"included) exceed the embedding model limit of {embedder.max_tokens}; "
                "split the section into smaller sections"
            )


def mean_pool_normalized(hidden_states: np.ndarray, attention_mask: np.ndarray) -> np.ndarray:
    """Mean over real (non-padding) tokens, then L2 normalisation, as the model card specifies."""
    mask = attention_mask[:, :, None].astype(np.float32)
    pooled = (hidden_states * mask).sum(axis=1) / mask.sum(axis=1)
    norms = np.linalg.norm(pooled, axis=1, keepdims=True)
    # A zero or non-finite vector has no direction; normalising it would produce NaN scores.
    if not np.all(np.isfinite(norms)) or np.any(norms == 0):
        raise EmbeddingError("the model produced a zero or non-finite embedding")
    return (pooled / norms).astype(np.float32)


class E5Embedder:
    """Loaded once per process. `embed` is a blocking CPU call."""

    def __init__(self, model_name: str, revision: str, cache_dir: Path):
        self.model_id = f"{model_name}@{revision}"
        self.max_tokens = E5_MAX_TOKENS
        # With a commit hash and the files already cached, no network request is made.
        tokenizer_path = hf_hub_download(
            model_name, "onnx/tokenizer.json", revision=revision, cache_dir=cache_dir
        )
        model_path = hf_hub_download(
            model_name, "onnx/model.onnx", revision=revision, cache_dir=cache_dir
        )
        self._tokenizer = Tokenizer.from_file(tokenizer_path)
        # Token counts must be real lengths, so the tokenizer must never cut an input short.
        self._tokenizer.no_truncation()
        self._pad_id = self._tokenizer.token_to_id("<pad>")
        self._session = onnxruntime.InferenceSession(model_path, providers=["CPUExecutionProvider"])
        # Measured from a real forward pass rather than assumed from the model card.
        self.dimension = self.embed([QUERY_PREFIX]).shape[1]

    def count_tokens(self, text: str) -> int:
        return len(self._tokenizer.encode(text).ids)

    def embed(self, texts: Sequence[str]) -> np.ndarray:
        batches = [
            self._embed_batch(texts[start : start + BATCH_SIZE])
            for start in range(0, len(texts), BATCH_SIZE)
        ]
        return np.concatenate(batches)

    def _embed_batch(self, texts: Sequence[str]) -> np.ndarray:
        encodings = self._tokenizer.encode_batch(list(texts))
        lengths = [len(encoding.ids) for encoding in encodings]
        if max(lengths) > self.max_tokens:
            raise EmbeddingError(
                f"input has {max(lengths)} tokens; the embedding model accepts at most "
                f"{self.max_tokens}"
            )
        input_ids = np.full((len(texts), max(lengths)), self._pad_id, dtype=np.int64)
        attention_mask = np.zeros_like(input_ids)
        for row, encoding in enumerate(encodings):
            input_ids[row, : lengths[row]] = encoding.ids
            attention_mask[row, : lengths[row]] = 1
        feeds = {
            "input_ids": input_ids,
            "attention_mask": attention_mask,
            "token_type_ids": np.zeros_like(input_ids),
        }
        hidden_states = self._session.run(["last_hidden_state"], feeds)[0]
        return mean_pool_normalized(hidden_states, attention_mask)
