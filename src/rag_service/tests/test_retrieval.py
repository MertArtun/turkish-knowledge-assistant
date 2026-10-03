from datetime import date

import numpy as np
import pytest

from app.contracts import Scope
from app.documents import load_corpus
from app.index_store import Index
from app.retrieval import retrieve
from app.versioning import DEFAULT_SCOPE, select_versions
from tests.corpus_files import KNOWLEDGE_DIR

CORPUS = load_corpus(KNOWLEDGE_DIR)
CHUNKS = {chunk.chunk_id: chunk for doc in CORPUS for chunk in doc.chunks}
TODAY = date(2026, 10, 4)


def unit(*values: float) -> np.ndarray:
    vector = np.array(values, dtype=np.float32)
    return vector / np.linalg.norm(vector)


def make_index(vectors: dict[str, np.ndarray]) -> Index:
    """An index over the given real chunks, in the given row order, with chosen vectors."""
    return Index(
        fingerprint="test",
        chunks=tuple(CHUNKS[chunk_id] for chunk_id in vectors),
        vectors=np.stack(list(vectors.values())),
    )


def decisions(as_of: date = TODAY, scope: Scope = DEFAULT_SCOPE):
    return select_versions([doc.metadata for doc in CORPUS], scope, as_of)


def ids(results) -> list[str]:
    return [result.chunk.chunk_id for result in results]


def test_expired_version_with_a_higher_score_is_never_returned_even_with_top_k_1():
    # D03 is the closest match, but it expired on 2026-07-01. Filtering after top-k would
    # return nothing here; filtering first returns the best chunk of the valid version.
    index = make_index(
        {"D03#sure": unit(1, 0), "D04#sure": unit(0.6, 0.8), "D08#saatler": unit(0, 1)}
    )

    results = retrieve(index, unit(1, 0), decisions(TODAY), top_k=1)

    assert ids(results) == ["D04#sure"]


def test_historical_date_searches_the_old_version_and_never_the_future_one():
    index = make_index({"D04#sure": unit(1, 0), "D03#sure": unit(0.6, 0.8)})

    results = retrieve(index, unit(1, 0), decisions(date(2026, 6, 30)), top_k=4)

    assert ids(results) == ["D03#sure"]


def test_unsupported_scope_returns_no_chunks_instead_of_falling_back_to_turkey():
    index = make_index({"D04#sure": unit(1, 0), "D08#saatler": unit(0, 1)})
    germany = Scope(country="DE", customer_type="B2B", product="MH-10")

    assert retrieve(index, unit(1, 0), decisions(scope=germany), top_k=4) == []


def test_equal_scores_are_ordered_by_chunk_id_whatever_the_row_order():
    same = unit(1, 1)
    index = make_index({"D08#saatler": same, "D05#bedel": same, "D01#baglanti": same})

    results = retrieve(index, unit(1, 1), decisions(), top_k=4)

    assert ids(results) == ["D01#baglanti", "D05#bedel", "D08#saatler"]


def test_results_are_sorted_by_score_and_cut_at_top_k():
    index = make_index(
        {
            "D01#baglanti": unit(0, 1),
            "D02#ses-yok": unit(1, 0),
            "D06#alanlar": unit(1, 1),
            "D09#sifre": unit(-1, 0),
        }
    )

    results = retrieve(index, unit(1, 0), decisions(), top_k=3)

    assert ids(results) == ["D02#ses-yok", "D06#alanlar", "D01#baglanti"]
    assert [result.score for result in results] == pytest.approx([1.0, 0.7071, 0.0], abs=1e-4)


def test_min_score_is_disabled_by_default_and_drops_weaker_chunks_when_set():
    index = make_index({"D02#ses-yok": unit(1, 0), "D09#sifre": unit(-1, 0)})

    unfiltered = retrieve(index, unit(1, 0), decisions(), top_k=4)
    filtered = retrieve(index, unit(1, 0), decisions(), top_k=4, min_score=0.5)

    assert ids(unfiltered) == ["D02#ses-yok", "D09#sifre"]
    assert ids(filtered) == ["D02#ses-yok"]
