"""Derived SQLite index of section embeddings.

The Markdown corpus is the source of truth and this file can always be rebuilt from it. A stored
index is served only when its fingerprint matches the current corpus and embedding model and every
stored vector passes validation. Otherwise the index is rebuilt into a temporary file, read back
with the same checks and moved into place with os.replace, so a half-written index is never served.
"""

import hashlib
import json
import logging
import os
import sqlite3
import tempfile
from collections.abc import Sequence
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from app.documents import Chunk, Document
from app.embeddings import Embedder, check_passage_lengths, passage_text

logger = logging.getLogger(__name__)

# Bump when the stored layout, the passage text format or the pooling changes: these change the
# vectors without changing any document, so the fingerprint must change with them.
INDEX_FORMAT_VERSION = 1
# Little-endian float32 bytes, read back with numpy.frombuffer: plain numbers, no pickle.
STORED_DTYPE = "<f4"
UNIT_NORM_TOLERANCE = 1e-3


class IndexStoreError(Exception):
    """A stored or freshly built index cannot be used."""


@dataclass(frozen=True)
class Index:
    fingerprint: str
    chunks: tuple[Chunk, ...]
    # float32 unit vectors, one row per chunk, in the same order as `chunks`.
    vectors: np.ndarray


def corpus_fingerprint(documents: Sequence[Document], model_id: str) -> str:
    """Changes whenever a document's content, metadata or file, the model or the format changes."""
    payload = {
        "index_format": INDEX_FORMAT_VERSION,
        "embedding_model": model_id,
        "documents": [
            {
                "file": doc.source_file,
                "metadata": doc.metadata.model_dump(mode="json"),
                # The passage text holds the prefix, heading path and verbatim content.
                "chunks": [[chunk.chunk_id, _sha256(passage_text(chunk))] for chunk in doc.chunks],
            }
            for doc in sorted(documents, key=lambda doc: doc.metadata.doc_id)
        ],
    }
    return _sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False))


def load_or_build_index(
    documents: Sequence[Document], embedder: Embedder, index_path: Path
) -> Index:
    """Startup entry point: reuse the stored index if it is current and valid, else rebuild it."""
    ordered = sorted(documents, key=lambda doc: doc.metadata.doc_id)
    chunks = tuple(chunk for doc in ordered for chunk in doc.chunks)
    check_passage_lengths(chunks, embedder)
    fingerprint = corpus_fingerprint(ordered, embedder.model_id)
    if index_path.exists():
        try:
            return _read_index(index_path, fingerprint, chunks, embedder.dimension)
        except IndexStoreError as error:
            logger.warning("rebuilding index %s: %s", index_path, error)
    else:
        logger.info("building index %s: no index file yet", index_path)
    return _build_index(index_path, fingerprint, chunks, embedder)


def _build_index(
    index_path: Path, fingerprint: str, chunks: tuple[Chunk, ...], embedder: Embedder
) -> Index:
    vectors = embedder.embed([passage_text(chunk) for chunk in chunks])
    # Checked before anything is written: invalid vectors fail startup and keep the old file.
    _check_vectors(vectors, chunks, embedder.dimension)
    index_path.parent.mkdir(parents=True, exist_ok=True)
    handle, temp_name = tempfile.mkstemp(
        dir=index_path.parent, prefix=f".{index_path.name}.", suffix=".tmp"
    )
    os.close(handle)
    temp_path = Path(temp_name)
    try:
        _write_index(temp_path, fingerprint, chunks, vectors)
        index = _read_index(temp_path, fingerprint, chunks, embedder.dimension)
        os.replace(temp_path, index_path)
    finally:
        temp_path.unlink(missing_ok=True)
    logger.info("built index %s with %d sections", index_path, len(chunks))
    return index


def _write_index(
    path: Path, fingerprint: str, chunks: tuple[Chunk, ...], vectors: np.ndarray
) -> None:
    with closing(sqlite3.connect(path)) as db, db:
        db.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        db.execute(
            "CREATE TABLE chunks ("
            "position INTEGER PRIMARY KEY, chunk_id TEXT NOT NULL UNIQUE, embedding BLOB NOT NULL)"
        )
        db.execute("INSERT INTO meta VALUES ('fingerprint', ?)", (fingerprint,))
        db.executemany(
            "INSERT INTO chunks VALUES (?, ?, ?)",
            [
                (position, chunk.chunk_id, vector.astype(STORED_DTYPE).tobytes())
                for position, (chunk, vector) in enumerate(zip(chunks, vectors, strict=True))
            ],
        )


def _read_index(path: Path, fingerprint: str, chunks: tuple[Chunk, ...], dimension: int) -> Index:
    try:
        with closing(sqlite3.connect(path)) as db:
            meta = dict(db.execute("SELECT key, value FROM meta").fetchall())
            rows = db.execute("SELECT chunk_id, embedding FROM chunks ORDER BY position").fetchall()
    except sqlite3.DatabaseError as error:
        raise IndexStoreError(f"unreadable index file: {error}") from error
    if meta.get("fingerprint") != fingerprint:
        raise IndexStoreError("fingerprint does not match the current corpus and embedding model")
    if [chunk_id for chunk_id, _ in rows] != [chunk.chunk_id for chunk in chunks]:
        raise IndexStoreError("stored sections do not match the corpus sections")
    expected_bytes = dimension * np.dtype(STORED_DTYPE).itemsize
    for chunk_id, blob in rows:
        if not isinstance(blob, bytes) or len(blob) != expected_bytes:
            raise IndexStoreError(
                f"{chunk_id}: stored vector does not have the model dimension {dimension}"
            )
    vectors = np.stack([np.frombuffer(blob, dtype=STORED_DTYPE) for _, blob in rows])
    _check_vectors(vectors, chunks, dimension)
    return Index(fingerprint=fingerprint, chunks=chunks, vectors=vectors)


def _check_vectors(vectors: np.ndarray, chunks: tuple[Chunk, ...], dimension: int) -> None:
    if vectors.shape != (len(chunks), dimension):
        raise IndexStoreError(
            f"expected {len(chunks)} vectors of dimension {dimension}, got shape {vectors.shape}"
        )
    # Retrieval scores are plain dot products, which are cosine similarities only for unit vectors.
    for chunk, vector in zip(chunks, vectors, strict=True):
        if not np.all(np.isfinite(vector)):
            raise IndexStoreError(f"{chunk.chunk_id}: embedding contains NaN or infinity")
        norm = float(np.linalg.norm(vector))
        if abs(norm - 1.0) > UNIT_NORM_TOLERANCE:
            raise IndexStoreError(f"{chunk.chunk_id}: embedding norm is {norm:.4f}, not 1")


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
