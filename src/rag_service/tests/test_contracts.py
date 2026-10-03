import copy
import json
from pathlib import Path

import pytest
from pydantic import BaseModel, ValidationError

from app.contracts import AskRequest, AskResponse, ErrorResponse, ReadinessResponse

# Shared with the .NET tests; both sides must accept and re-serialize the same JSON.
FIXTURE_DIR = Path(__file__).resolve().parents[3] / "tests" / "contracts"

FIXTURE_MODELS: dict[str, type[BaseModel]] = {
    "ask-request.json": AskRequest,
    "ask-response-answered.json": AskResponse,
    "ask-response-partial.json": AskResponse,
    "ask-response-insufficient-evidence.json": AskResponse,
    "ask-response-evidence-only.json": AskResponse,
    "error-response.json": ErrorResponse,
    "readiness-not-ready.json": ReadinessResponse,
}


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


def test_unknown_error_code_is_rejected():
    raw = load_fixture("error-response.json")
    raw["error"]["code"] = "something_else"

    with pytest.raises(ValidationError):
        ErrorResponse.model_validate(raw)
