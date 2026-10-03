"""Checks against the real pinned model. Run with: uv run pytest -m model

The first run downloads the model files into MODEL_CACHE_DIR (internet needed once).
"""

from dataclasses import replace
from datetime import date
from pathlib import Path

import numpy as np
import onnxruntime
import pytest
from huggingface_hub import hf_hub_download

from app.documents import CorpusError, load_corpus
from app.embeddings import E5Embedder, EmbeddingError, check_passage_lengths, embed_query
from app.index_store import load_or_build_index
from app.retrieval import retrieve
from app.settings import load_settings
from app.versioning import DEFAULT_SCOPE, select_versions
from tests.corpus_files import KNOWLEDGE_DIR

pytestmark = pytest.mark.model

SERVICE_ROOT = Path(__file__).resolve().parents[1]
SETTINGS = load_settings({})
# Settings paths are relative to src/rag_service; resolve them so pytest's cwd does not matter.
CACHE_DIR = SERVICE_ROOT / SETTINGS.model_cache_dir


@pytest.fixture(scope="module")
def embedder() -> E5Embedder:
    return E5Embedder(SETTINGS.embedding_model, SETTINGS.embedding_revision, CACHE_DIR)


def test_pinned_model_produces_384_dimensional_unit_vectors(embedder):
    vectors = embedder.embed(["query: İade süresi nedir?", "passage: Destek saatleri"])

    assert embedder.dimension == 384
    assert vectors.shape == (2, 384)
    assert vectors.dtype == np.float32
    np.testing.assert_allclose(np.linalg.norm(vectors, axis=1), 1.0, atol=1e-5)


def test_model_file_accepts_512_positions_and_fails_at_513(embedder):
    model_path = hf_hub_download(
        SETTINGS.embedding_model,
        "onnx/model.onnx",
        revision=SETTINGS.embedding_revision,
        cache_dir=CACHE_DIR,
        local_files_only=True,
    )
    session = onnxruntime.InferenceSession(model_path, providers=["CPUExecutionProvider"])

    def run(length: int) -> np.ndarray:
        ids = np.full((1, length), 6, dtype=np.int64)
        feeds = {
            "input_ids": ids,
            "attention_mask": np.ones_like(ids),
            "token_type_ids": np.zeros_like(ids),
        }
        return session.run(["last_hidden_state"], feeds)[0]

    assert embedder.max_tokens == 512
    assert run(512).shape == (1, 512, 384)
    with pytest.raises(Exception, match="512 by 513"):
        run(513)


def test_token_count_includes_special_tokens_and_is_never_truncated(embedder):
    long_text = "passage: " + "kelime " * 600

    assert embedder.count_tokens("") == 2  # <s> and </s>
    assert embedder.count_tokens(long_text) > 600


def test_embedding_an_input_over_the_limit_is_refused_instead_of_truncated(embedder):
    with pytest.raises(EmbeddingError, match="512"):
        embedder.embed(["query: " + "kelime " * 600])


def test_every_real_corpus_section_fits_the_model_input(embedder):
    chunks = [chunk for doc in load_corpus(KNOWLEDGE_DIR) for chunk in doc.chunks]

    check_passage_lengths(chunks, embedder)


def test_too_long_section_is_a_load_error_with_the_real_tokenizer(embedder):
    chunk = load_corpus(KNOWLEDGE_DIR)[3].chunks[1]
    too_long = replace(chunk, content=chunk.content + " Ek açıklama." * 200)

    with pytest.raises(CorpusError, match=rf"{chunk.chunk_id}: \d+ tokens"):
        check_passage_lengths([too_long], embedder)


def test_password_reset_question_finds_the_account_access_document(embedder, tmp_path):
    corpus = load_corpus(KNOWLEDGE_DIR)
    index = load_or_build_index(corpus, embedder, tmp_path / "index.sqlite3")
    view = select_versions([doc.metadata for doc in corpus], DEFAULT_SCOPE, date(2026, 10, 4))
    question = "Parola sıfırlama e-postası hangi adrese gönderilir?"

    results = retrieve(index, embed_query(embedder, question), view, top_k=4)

    assert results[0].chunk.doc_id == "D09"
