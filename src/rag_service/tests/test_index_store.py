import dataclasses
import logging
import shutil
import sqlite3
from contextlib import closing
from pathlib import Path

import numpy as np
import pytest

from app.documents import CorpusError, load_corpus
from app.embeddings import passage_text
from app.index_store import IndexStoreError, corpus_fingerprint, load_or_build_index
from tests.corpus_files import KNOWLEDGE_DIR
from tests.fake_embedder import FakeEmbedder


@pytest.fixture
def corpus():
    return load_corpus(KNOWLEDGE_DIR)


@pytest.fixture
def index_path(tmp_path: Path) -> Path:
    return tmp_path / "var" / "index.sqlite3"


def copy_of_real_corpus(tmp_path: Path) -> Path:
    knowledge = tmp_path / "knowledge"
    shutil.copytree(KNOWLEDGE_DIR, knowledge)
    return knowledge


def stored_fingerprint(index_path: Path) -> str:
    with closing(sqlite3.connect(index_path)) as db:
        return db.execute("SELECT value FROM meta WHERE key = 'fingerprint'").fetchone()[0]


def all_chunk_ids(documents) -> list[str]:
    return [chunk.chunk_id for doc in documents for chunk in doc.chunks]


# --- Build and reuse -------------------------------------------------------------------------


def test_first_start_builds_the_index_and_the_next_start_reuses_it(corpus, index_path):
    built = load_or_build_index(corpus, FakeEmbedder(), index_path)
    second_embedder = FakeEmbedder()

    reused = load_or_build_index(corpus, second_embedder, index_path)

    assert index_path.exists()
    assert [chunk.chunk_id for chunk in built.chunks] == all_chunk_ids(corpus)
    assert second_embedder.embedded_texts == []
    assert reused.fingerprint == built.fingerprint == stored_fingerprint(index_path)
    np.testing.assert_array_equal(reused.vectors, built.vectors)


def test_every_section_is_embedded_as_a_passage_with_its_heading_path(corpus, index_path):
    embedder = FakeEmbedder()

    load_or_build_index(corpus, embedder, index_path)

    assert embedder.embedded_texts == [
        passage_text(chunk) for doc in corpus for chunk in doc.chunks
    ]


def test_embeddings_are_stored_as_little_endian_float32_bytes(corpus, index_path):
    index = load_or_build_index(corpus, FakeEmbedder(), index_path)

    with closing(sqlite3.connect(index_path)) as db:
        blob = db.execute("SELECT embedding FROM chunks ORDER BY position LIMIT 1").fetchone()[0]

    assert len(blob) == index.vectors.shape[1] * 4
    np.testing.assert_array_equal(np.frombuffer(blob, dtype="<f4"), index.vectors[0])


# --- Stale index -----------------------------------------------------------------------------


def test_metadata_change_makes_the_stored_index_stale(tmp_path, index_path):
    knowledge = copy_of_real_corpus(tmp_path)
    first = load_or_build_index(load_corpus(knowledge), FakeEmbedder(), index_path)
    d10 = knowledge / "10-safe-support-sharing.md"
    d10.write_text(
        d10.read_text(encoding="utf-8").replace("valid_to: null", "valid_to: 2027-01-01"),
        encoding="utf-8",
    )
    embedder = FakeEmbedder()

    second = load_or_build_index(load_corpus(knowledge), embedder, index_path)

    assert embedder.embedded_texts, "a metadata change must rebuild the index"
    assert second.fingerprint != first.fingerprint
    assert stored_fingerprint(index_path) == second.fingerprint


def test_deleted_document_is_not_served_from_the_old_index(tmp_path, index_path):
    knowledge = copy_of_real_corpus(tmp_path)
    load_or_build_index(load_corpus(knowledge), FakeEmbedder(), index_path)
    (knowledge / "10-safe-support-sharing.md").unlink()
    embedder = FakeEmbedder()

    index = load_or_build_index(load_corpus(knowledge), embedder, index_path)

    assert embedder.embedded_texts
    assert not [chunk for chunk in index.chunks if chunk.doc_id == "D10"]


def test_model_revision_change_makes_the_stored_index_stale(corpus, index_path):
    rev1 = load_or_build_index(corpus, FakeEmbedder(model_id="fake-e5@rev1"), index_path)
    embedder = FakeEmbedder(model_id="fake-e5@rev2")

    rev2 = load_or_build_index(corpus, embedder, index_path)

    assert embedder.embedded_texts
    assert rev2.fingerprint != rev1.fingerprint
    assert not np.array_equal(rev2.vectors, rev1.vectors)


def test_fingerprint_covers_content_metadata_and_model_but_not_document_order(corpus):
    base = corpus_fingerprint(corpus, "model@rev1")
    d04 = corpus[3]
    changed_metadata = dataclasses.replace(
        d04, metadata=d04.metadata.model_copy(update={"status": "withdrawn"})
    )
    changed_content = dataclasses.replace(
        d04,
        chunks=(dataclasses.replace(d04.chunks[0], content="Başka bir metin."), *d04.chunks[1:]),
    )

    assert corpus_fingerprint(list(reversed(corpus)), "model@rev1") == base
    assert corpus_fingerprint(corpus, "model@rev2") != base
    assert corpus_fingerprint([*corpus[:3], changed_metadata, *corpus[4:]], "model@rev1") != base
    assert corpus_fingerprint([*corpus[:3], changed_content, *corpus[4:]], "model@rev1") != base


# --- Invalid stored index --------------------------------------------------------------------


def write_garbage(index_path: Path) -> None:
    index_path.write_bytes(b"this is not an SQLite database")


def run_sql(statement: str, *params):
    def damage(index_path: Path) -> None:
        with closing(sqlite3.connect(index_path)) as db, db:
            db.execute(statement, params)

    return damage


DIMENSION = FakeEmbedder().dimension
NAN_VECTOR = np.full(DIMENSION, np.nan, dtype="<f4").tobytes()
ZERO_VECTOR = np.zeros(DIMENSION, dtype="<f4").tobytes()
SHORT_VECTOR = np.ones(DIMENSION - 1, dtype="<f4").tobytes()


@pytest.mark.parametrize(
    "damage",
    [
        write_garbage,
        run_sql("UPDATE chunks SET embedding = ? WHERE position = 0", NAN_VECTOR),
        run_sql("UPDATE chunks SET embedding = ? WHERE position = 0", ZERO_VECTOR),
        run_sql("UPDATE chunks SET embedding = ? WHERE position = 0", SHORT_VECTOR),
        run_sql("DELETE FROM chunks WHERE position = 3"),
        run_sql("UPDATE chunks SET chunk_id = 'D99#x' WHERE position = 0"),
        run_sql("DROP TABLE meta"),
    ],
    ids=[
        "not-sqlite",
        "nan",
        "zero-norm",
        "dimension-mismatch",
        "missing-row",
        "unknown-chunk",
        "missing-table",
    ],
)
def test_invalid_stored_index_is_rebuilt_instead_of_served(corpus, index_path, damage, caplog):
    built = load_or_build_index(corpus, FakeEmbedder(), index_path)
    damage(index_path)
    embedder = FakeEmbedder()

    with caplog.at_level(logging.WARNING, logger="app.index_store"):
        index = load_or_build_index(corpus, embedder, index_path)

    assert embedder.embedded_texts, "the damaged index must not be served"
    assert "rebuilding" in caplog.text
    np.testing.assert_array_equal(index.vectors, built.vectors)
    assert load_or_build_index(corpus, FakeEmbedder(), index_path).fingerprint == built.fingerprint


@pytest.mark.parametrize(
    ("poison", "message"),
    [("nan", "D01#kullanim"), ("zero", "D01#kullanim"), ("short", "dimension")],
)
def test_invalid_new_embeddings_fail_the_build_and_keep_the_previous_index(
    corpus, index_path, poison, message
):
    previous = load_or_build_index(corpus, FakeEmbedder(model_id="fake-e5@rev1"), index_path)

    with pytest.raises(IndexStoreError, match=message):
        load_or_build_index(
            corpus, FakeEmbedder(model_id="fake-e5@rev2", poison=poison), index_path
        )

    assert stored_fingerprint(index_path) == previous.fingerprint
    assert sorted(path.name for path in index_path.parent.iterdir()) == [index_path.name]


def test_section_over_the_token_limit_stops_startup_before_any_index_is_written(corpus, index_path):
    with pytest.raises(CorpusError, match="tokens"):
        load_or_build_index(corpus, FakeEmbedder(max_tokens=10), index_path)

    assert not index_path.exists()
