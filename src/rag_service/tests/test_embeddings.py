import numpy as np
import pytest

from app.documents import Chunk, CorpusError
from app.embeddings import (
    EmbeddingError,
    check_passage_lengths,
    embed_query,
    mean_pool_normalized,
    passage_text,
    query_text,
)
from tests.fake_embedder import FakeEmbedder


def make_chunk(content: str = "İade talebi teslimden itibaren 30 takvim günü içinde açılabilir."):
    return Chunk(
        chunk_id="D04#sure",
        doc_id="D04",
        section_id="sure",
        heading_path=("MH-10 İade Prosedürü", "İade süresi"),
        content=content,
        content_hash="not-checked-here",
    )


def test_passage_input_has_the_passage_prefix_heading_path_and_verbatim_content():
    chunk = make_chunk()

    assert passage_text(chunk) == (
        "passage: MH-10 İade Prosedürü > İade süresi\n"
        "İade talebi teslimden itibaren 30 takvim günü içinde açılabilir."
    )


def test_query_input_has_the_query_prefix():
    assert query_text("İade kargosunu kim ödüyor?") == "query: İade kargosunu kim ödüyor?"


def test_queries_are_embedded_with_the_query_prefix():
    embedder = FakeEmbedder()

    vector = embed_query(embedder, "Destek saatleri nedir?")

    assert embedder.embedded_texts == ["query: Destek saatleri nedir?"]
    assert vector.shape == (embedder.dimension,)


def test_token_length_is_measured_on_the_full_model_input():
    chunk = make_chunk()
    embedder = FakeEmbedder()

    check_passage_lengths([chunk], embedder)

    assert embedder.counted_texts == [passage_text(chunk)]


def test_section_at_the_token_limit_is_accepted_and_one_more_token_is_a_load_error():
    chunk = make_chunk()
    limit = FakeEmbedder().count_tokens(passage_text(chunk))

    check_passage_lengths([chunk], FakeEmbedder(max_tokens=limit))
    with pytest.raises(CorpusError, match=rf"D04#sure.*{limit} tokens.*{limit - 1}"):
        check_passage_lengths([chunk], FakeEmbedder(max_tokens=limit - 1))


def test_mean_pooling_ignores_padding_and_returns_unit_vectors():
    hidden = np.array(
        [
            [[1.0, 0.0], [3.0, 0.0], [100.0, 100.0]],  # last position is padding
            [[0.0, 2.0], [0.0, 4.0], [0.0, 6.0]],
        ],
        dtype=np.float32,
    )
    mask = np.array([[1, 1, 0], [1, 1, 1]])

    pooled = mean_pool_normalized(hidden, mask)

    np.testing.assert_allclose(pooled, [[1.0, 0.0], [0.0, 1.0]], atol=1e-6)
    assert pooled.dtype == np.float32


@pytest.mark.parametrize("bad_value", [0.0, np.nan, np.inf])
def test_zero_or_non_finite_embedding_is_an_error_not_a_vector(bad_value):
    hidden = np.full((1, 2, 3), bad_value, dtype=np.float32)

    with pytest.raises(EmbeddingError):
        mean_pool_normalized(hidden, np.ones((1, 2), dtype=np.int64))
