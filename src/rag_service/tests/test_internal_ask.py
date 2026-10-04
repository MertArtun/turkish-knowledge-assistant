import json
import re

import pytest
from fastapi.testclient import TestClient

from app.contracts import AskResponse, ErrorResponse
from app.generation import GenerationError
from app.main import create_app
from app.service import Assistant
from tests.fake_assistant import QueryEmbedder, make_assistant
from tests.fake_generator import FakeGenerator, model_answer

GENERATED_ID = re.compile(r"[0-9a-f]{32}")
QUESTION = "İade kargosunu kim ödüyor?"


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app(make_assistant({"D04#kargo": 0.9, "D04#sure": 0.8})))


def post(client: TestClient, body, request_id: str | None = None, **headers):
    if request_id is not None:
        headers["X-Request-ID"] = request_id
    content = body if isinstance(body, str) else json.dumps(body)
    return client.post(
        "/internal/ask",
        content=content,
        headers={"Content-Type": "application/json", **headers},
    )


def error_of(response) -> ErrorResponse:
    # Exactly the error contract: no FastAPI "detail", no echoed input.
    assert list(response.json()) == ["request_id", "error"]
    return ErrorResponse.model_validate(response.json())


def test_valid_request_returns_the_contract_body_with_the_callers_request_id(client):
    response = post(client, {"question": QUESTION}, request_id="eval-E04.run_1")

    assert response.status_code == 200
    answer = AskResponse.model_validate(response.json())
    assert answer.request_id == "eval-E04.run_1"
    assert response.headers["X-Request-ID"] == "eval-E04.run_1"
    assert answer.status == "evidence_only"
    assert answer.retrieved_chunk_ids[:2] == ["D04#kargo", "D04#sure"]


def test_request_as_sent_by_the_dotnet_api_with_explicit_nulls_is_accepted(client):
    body = {"question": QUESTION, "as_of": None, "scope": None, "mode": None}

    response = post(client, body, request_id="abc")

    assert response.status_code == 200
    assert response.json()["effective_scope"] == {
        "country": "TR",
        "customer_type": "B2B",
        "product": "MH-10",
    }


@pytest.mark.parametrize("incoming", [None, "", "has space", "semi;colon", "a" * 65])
def test_missing_or_unsafe_request_id_is_replaced_by_a_generated_one(client, incoming):
    response = post(client, {"question": QUESTION}, request_id=incoming)

    generated = response.json()["request_id"]
    assert GENERATED_ID.fullmatch(generated)
    assert response.headers["X-Request-ID"] == generated


def test_two_request_id_headers_are_not_trusted(client):
    response = client.post(
        "/internal/ask",
        json={"question": QUESTION},
        headers=[("X-Request-ID", "first"), ("X-Request-ID", "second")],
    )

    assert GENERATED_ID.fullmatch(response.json()["request_id"])


@pytest.mark.parametrize(
    "body",
    [
        "not json",
        "",
        {},
        {"question": "   "},
        {"question": "a" * 2001},
        {"question": QUESTION, "mode": "chat"},
        {"question": QUESTION, "as_of": "2026-10-04T00:00:00"},
        {"question": QUESTION, "extra": 1},
        {
            "question": QUESTION,
            "scope": {"country": "T" * 65, "customer_type": "B2B", "product": "x"},
        },
    ],
)
def test_invalid_request_is_400_invalid_request_not_fastapis_422(client, body):
    response = post(client, body, request_id="req-bad")

    assert response.status_code == 400
    error = error_of(response)
    assert (error.request_id, error.error.code) == ("req-bad", "invalid_request")
    assert QUESTION not in response.text


def test_generative_request_without_generation_is_503_generation_not_configured(client):
    response = post(client, {"question": QUESTION, "mode": "generative"}, request_id="req-gen")

    assert response.status_code == 503
    error = error_of(response)
    assert (error.request_id, error.error.code) == ("req-gen", "generation_not_configured")
    assert response.headers["X-Request-ID"] == "req-gen"


def test_question_over_the_model_token_limit_is_400_invalid_request():
    client = TestClient(create_app(make_assistant(embedder=QueryEmbedder(max_tokens=4))))

    response = post(client, {"question": "bir iki üç dört beş"}, request_id="req-long")

    assert response.status_code == 400
    assert error_of(response).error.code == "invalid_request"


def test_unexpected_error_is_500_internal_error_without_its_text(monkeypatch):
    async def broken_ask(self, request, request_id):
        raise RuntimeError("boom in /srv/app/secret.py")

    monkeypatch.setattr(Assistant, "ask", broken_ask)
    client = TestClient(create_app(make_assistant()), raise_server_exceptions=False)

    response = post(client, {"question": QUESTION}, request_id="req-500")

    assert response.status_code == 500
    error = error_of(response)
    assert (error.request_id, error.error.code) == ("req-500", "internal_error")
    assert response.headers["X-Request-ID"] == "req-500"
    assert "boom" not in response.text
    assert "secret" not in response.text


def test_generative_answer_is_200_with_the_contract_body():
    claim = "Şirket iade etiketi sağlar ve bu etiketle yapılan gönderimin bedelini karşılar."
    generator = FakeGenerator(model_answer("answered", [(claim, ["S1"])]))
    client = TestClient(create_app(make_assistant({"D04#kargo": 0.9}, generator=generator)))

    response = post(client, {"question": QUESTION, "mode": "generative"}, request_id="req-gen")

    assert response.status_code == 200
    answer = AskResponse.model_validate(response.json())
    assert (answer.status, answer.answer, answer.request_id) == ("answered", claim, "req-gen")
    assert [source.chunk_id for source in answer.sources] == ["D04#kargo"]


@pytest.mark.parametrize(
    ("code", "status"),
    [
        ("provider_unavailable", 503),
        ("generation_timeout", 504),
        ("invalid_generation_output", 502),
    ],
)
def test_generation_failures_have_their_own_status_and_safe_message(code, status):
    detail = "status=401 code='invalid_api_key'"
    generator = FakeGenerator(error=GenerationError(code, detail))
    client = TestClient(create_app(make_assistant({"D04#kargo": 0.9}, generator=generator)))

    response = post(client, {"question": QUESTION, "mode": "generative"}, request_id="req-fail")

    assert response.status_code == status
    error = error_of(response)
    assert (error.request_id, error.error.code) == ("req-fail", code)
    assert "invalid_api_key" not in response.text
    assert QUESTION not in response.text
