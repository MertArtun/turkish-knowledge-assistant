import copy
import json
from pathlib import Path

import pytest
from pydantic import BaseModel, ValidationError

from app.contracts import AskRequest, AskResponse, ErrorResponse, ReadinessResponse
from app.documents import load_corpus
from tests.corpus_files import KNOWLEDGE_DIR

# Shared with the .NET tests; both sides must accept and re-serialize the same JSON.
FIXTURE_DIR = Path(__file__).resolve().parents[3] / "tests" / "contracts"

FIXTURE_MODELS: dict[str, type[BaseModel]] = {
    "ask-request.json": AskRequest,
    "ask-response-answered.json": AskResponse,
    "ask-response-partial.json": AskResponse,
    "ask-response-insufficient-evidence.json": AskResponse,
    "ask-response-evidence-only.json": AskResponse,
    "error-response.json": ErrorResponse,
    "readiness-ready.json": ReadinessResponse,
}
RESPONSE_FIXTURES = [name for name, model in FIXTURE_MODELS.items() if model is AskResponse]


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def test_every_fixture_file_has_a_model():
    assert sorted(path.name for path in FIXTURE_DIR.glob("*.json")) == sorted(FIXTURE_MODELS)


@pytest.mark.parametrize(("name", "model"), FIXTURE_MODELS.items())
def test_fixture_round_trips_without_changes(name, model):
    raw = load_fixture(name)

    assert model.model_validate(raw).model_dump(mode="json") == raw


@pytest.mark.parametrize("name", [n for n, m in FIXTURE_MODELS.items() if m is not AskRequest])
def test_unknown_fields_are_rejected(name):
    raw = load_fixture(name)
    raw["unexpected"] = True

    with pytest.raises(ValidationError):
        FIXTURE_MODELS[name].model_validate(raw)


def request_with(**changes) -> dict:
    raw = load_fixture("ask-request.json")
    raw.update(changes)
    return raw


def test_minimal_request_uses_server_defaults():
    request = AskRequest.model_validate({"question": "Destek saatleri nedir?"})

    assert request.as_of is None
    assert request.scope is None
    assert request.mode is None


def test_question_is_trimmed_and_limited_after_trimming():
    request = AskRequest.model_validate(request_with(question="  " + "a" * 2000 + "  "))

    assert len(request.question) == 2000


@pytest.mark.parametrize(
    "changes",
    [
        {"question": "   "},
        {"question": "a" * 2001},
        {"mode": "chat"},
        {"as_of": "04.10.2026"},
        {"as_of": "2026-10-04T00:00:00"},
        {"as_of": 1790035200},
        {"as_of": "2026-02-30"},
        {"scope": {"country": "TR", "customer_type": "B2B"}},
        {"scope": {"country": "TR", "customer_type": "B2B", "product": "MH-10", "region": "x"}},
        {"extra_field": 1},
    ],
)
def test_invalid_requests_are_rejected(changes):
    with pytest.raises(ValidationError):
        AskRequest.model_validate(request_with(**changes))


def response_with(name: str, **changes) -> dict:
    raw = copy.deepcopy(load_fixture(name))
    raw.update(changes)
    return raw


@pytest.mark.parametrize(
    ("name", "changes"),
    [
        # A claim must cite something that is listed in sources, and sources must all be cited.
        ("ask-response-answered.json", {"sources": []}),
        ("ask-response-answered.json", {"missing_topics": ["x"]}),
        ("ask-response-answered.json", {"claims": [], "sources": []}),
        ("ask-response-partial.json", {"missing_topics": []}),
        ("ask-response-insufficient-evidence.json", {"reason_code": None}),
        ("ask-response-insufficient-evidence.json", {"answer": None}),
        ("ask-response-evidence-only.json", {"answer": "Uydurma cevap"}),
        ("ask-response-evidence-only.json", {"evidence": []}),
        ("ask-response-evidence-only.json", {"mode": "generative"}),
        ("ask-response-answered.json", {"mode": "evidence_only"}),
    ],
)
def test_status_and_content_must_agree(name, changes):
    with pytest.raises(ValidationError):
        AskResponse.model_validate(response_with(name, **changes))


def test_claim_without_source_ids_is_rejected():
    raw = response_with("ask-response-answered.json")
    raw["claims"][0]["source_chunk_ids"] = []

    with pytest.raises(ValidationError):
        AskResponse.model_validate(raw)


@pytest.mark.parametrize(
    ("field", "value"),
    [("status", "not_ready"), ("corpus_fingerprint", None), ("prompt_hash", None)],
)
def test_readiness_only_describes_a_fully_loaded_service(field, value):
    # The service loads the corpus, model and index before it accepts connections, so it never
    # reports "not ready" or a missing fingerprint; while it loads, its port is simply closed.
    raw = copy.deepcopy(load_fixture("readiness-ready.json"))
    target = raw if field == "status" else raw["run_metadata"]
    target[field] = value

    with pytest.raises(ValidationError):
        ReadinessResponse.model_validate(raw)


def test_unknown_error_code_is_rejected():
    raw = load_fixture("error-response.json")
    raw["error"]["code"] = "something_else"

    with pytest.raises(ValidationError):
        ErrorResponse.model_validate(raw)


@pytest.mark.parametrize("name", RESPONSE_FIXTURES)
def test_response_fixtures_cite_the_real_corpus_verbatim(name):
    # Fixtures are examples, but their sources must still be real sections quoted exactly, so the
    # contract examples never show a quote the service could not produce.
    corpus = load_corpus(KNOWLEDGE_DIR)
    documents = {doc.metadata.doc_id: doc for doc in corpus}
    chunks = {chunk.chunk_id: chunk for doc in corpus for chunk in doc.chunks}
    response = AskResponse.model_validate(load_fixture(name))

    assert set(response.retrieved_chunk_ids) <= set(chunks)
    for source in response.sources + response.evidence:
        chunk = chunks[source.chunk_id]
        metadata = documents[chunk.doc_id].metadata
        assert (source.doc_id, source.section_id) == (chunk.doc_id, chunk.section_id)
        assert source.quote == chunk.content
        assert tuple(source.heading_path) == chunk.heading_path
        assert source.document_title == metadata.title
        assert (source.version, source.valid_from, source.valid_to) == (
            metadata.version,
            metadata.valid_from,
            metadata.valid_to,
        )
