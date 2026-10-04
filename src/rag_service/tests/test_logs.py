"""What the RAG service writes to its log.

One JSON object per line, with the fields needed to follow a request (request ID, mode, outcome,
chunk and version IDs, timings, error codes) and never the question, an answer or a document's
text. Records are captured with caplog and rendered by the same formatter that log_config.json
gives uvicorn.
"""

import json
import logging
import sys

import pydantic
import pytest
from fastapi.testclient import TestClient

from app.contracts import AskResponse
from app.generation import GenerationError, load_system_prompt
from app.logs import JsonFormatter
from app.main import create_app
from tests.fake_assistant import CHUNKS, QueryEmbedder, make_assistant
from tests.fake_generator import FakeGenerator, model_answer

# A marker that can only reach the log by copying the question.
MARKER = "gizli-ayrıntı-4711"
QUESTION = f"İade kargosunu kim ödüyor? {MARKER}"
CLAIM = "Şirket iade etiketi sağlar ve bu etiketle yapılan gönderimin bedelini karşılar."
MISSING_TOPIC = "Almanya'daki iade koşulu gizli-eksik-konu"
SCORES = {"D04#kargo": 0.9, "D05#bedel": 0.8}
GERMANY = {"country": "DE", "customer_type": "B2B", "product": "MH-10"}


def post(client: TestClient, body: dict, request_id: str = "req-log"):
    return client.post("/internal/ask", json=body, headers={"X-Request-ID": request_id})


def log_lines(caplog) -> list[dict]:
    formatter = JsonFormatter()
    # json.loads fails the test if any record is not a single JSON object.
    return [json.loads(formatter.format(record)) for record in caplog.records]


def events(caplog, message: str) -> list[dict]:
    return [line for line in log_lines(caplog) if line["message"] == message]


SCENARIOS = {
    "evidence_only": ({}, {"question": QUESTION}),
    "generative_answered": (
        {"generator": FakeGenerator(model_answer("answered", [(CLAIM, ["D04#kargo"])]))},
        {"question": QUESTION, "mode": "generative"},
    ),
    "generative_partial": (
        {
            "generator": FakeGenerator(
                model_answer("partial", [(CLAIM, ["D04#kargo"])], missing_topics=[MISSING_TOPIC])
            )
        },
        {"question": QUESTION, "mode": "generative"},
    ),
    "generative_unverifiable_output": (
        {"generator": FakeGenerator(model_answer("answered", [(CLAIM, ["D08#saatler"])]))},
        {"question": QUESTION, "mode": "generative"},
    ),
    "provider_error": (
        {
            "generator": FakeGenerator(
                error=GenerationError("provider_unavailable", "status=429 code='quota'")
            )
        },
        {"question": QUESTION, "mode": "generative"},
    ),
    "generation_not_configured": ({}, {"question": QUESTION, "mode": "generative"}),
    "unsupported_scope": ({}, {"question": QUESTION, "scope": GERMANY}),
    "question_over_the_token_limit": (
        {"embedder": QueryEmbedder(max_tokens=3)},
        {"question": QUESTION},
    ),
    "invalid_request": ({}, {"question": QUESTION + " " + "x" * 2000}),
}


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_log_never_contains_the_question_the_answer_or_document_text(caplog, scenario):
    caplog.set_level(logging.INFO)
    assistant_options, body = SCENARIOS[scenario]
    client = TestClient(create_app(make_assistant(SCORES, **assistant_options)))

    response = post(client, body)

    written = "\n".join(json.dumps(line, ensure_ascii=False) for line in log_lines(caplog))
    assert MARKER not in written
    assert CLAIM not in written
    assert "gizli-eksik-konu" not in written
    assert CHUNKS["D04#kargo"].content not in written
    # Not vacuous: the request was logged, under its ID.
    assert response.headers["X-Request-ID"] == "req-log"
    assert any(line.get("request_id") == "req-log" for line in log_lines(caplog))


def test_answer_line_names_outcome_sections_versions_and_timings(caplog):
    caplog.set_level(logging.INFO)
    client = TestClient(create_app(make_assistant(SCORES)))

    post(client, {"question": QUESTION, "as_of": "2026-10-04"}, request_id="req-1")

    (line,) = events(caplog, "ask")
    assert (line["request_id"], line["mode"], line["outcome"]) == (
        "req-1",
        "evidence_only",
        "evidence_only",
    )
    # Scores live in the log, never in the response.
    assert line["retrieved"][:2] == [
        {"chunk_id": "D04#kargo", "score": pytest.approx(0.9, abs=1e-4)},
        {"chunk_id": "D05#bedel", "score": pytest.approx(0.8, abs=1e-4)},
    ]
    # The document versions the retrieved sections come from, in first-appearance order.
    assert line["versions"][:2] == ["D04@2.0", "D05@1.0"]
    assert all(line[key] >= 0 for key in ("embed_ms", "search_ms", "total_ms"))
    assert line["corpus"] == "test-fingerprint"[:12]


def test_generation_line_names_model_prompt_tokens_and_timing(caplog):
    caplog.set_level(logging.INFO)
    generator = FakeGenerator(model_answer("answered", [(CLAIM, ["D04#kargo"])]))
    client = TestClient(create_app(make_assistant(SCORES, generator=generator)))

    post(client, {"question": QUESTION, "mode": "generative"}, request_id="req-2")

    (line,) = events(caplog, "generation")
    prompt = load_system_prompt()
    assert (line["request_id"], line["outcome"], line["cited"]) == (
        "req-2",
        "answered",
        ["D04#kargo"],
    )
    assert (line["model"], line["prompt"]) == (
        "fake-model",
        f"{prompt.version}@{prompt.sha256[:12]}",
    )
    assert line["generate_ms"] >= 0
    assert {"input_tokens", "output_tokens", "reasoning_tokens"} <= set(line)
    assert events(caplog, "ask")[0]["outcome"] == "answered"


def test_generation_failure_line_names_the_code_and_the_safe_detail(caplog):
    caplog.set_level(logging.INFO)
    error = GenerationError("provider_unavailable", "status=429 code='insufficient_quota'")
    client = TestClient(create_app(make_assistant(SCORES, generator=FakeGenerator(error=error))))

    post(client, {"question": QUESTION, "mode": "generative"}, request_id="req-3")

    (line,) = events(caplog, "generation")
    assert (line["request_id"], line["outcome"]) == ("req-3", "provider_unavailable")
    assert line["detail"] == "status=429 code='insufficient_quota'"
    (refused,) = events(caplog, "refused")
    assert (refused["request_id"], refused["code"]) == ("req-3", "provider_unavailable")


def test_unsafe_request_id_never_reaches_the_log(caplog):
    caplog.set_level(logging.INFO)
    client = TestClient(create_app(make_assistant(SCORES)))

    response = post(client, {"question": QUESTION}, request_id="forged; level=ERROR")

    written = json.dumps(log_lines(caplog))
    assert "forged" not in written
    assert response.json()["request_id"] in written


def test_record_becomes_one_json_object_with_its_fields():
    record = logging.LogRecord(
        "uvicorn.error", logging.INFO, __file__, 1, "Started server process [%d]", (42,), None
    )
    record.fields = {"request_id": "abc", "embed_ms": 4.2}

    line = json.loads(JsonFormatter().format(record))

    assert line["level"] == "INFO"
    assert line["logger"] == "uvicorn.error"
    assert line["message"] == "Started server process [42]"
    assert (line["request_id"], line["embed_ms"]) == ("abc", 4.2)
    assert line["time"].endswith("+00:00")


def test_exception_is_logged_by_type_and_location_never_by_its_message():
    # pydantic repeats the invalid input in its message, so an unexpected failure while building
    # a response could otherwise copy answer or document text into the log.
    try:
        AskResponse.model_validate({"request_id": "r", "answer": QUESTION})
    except pydantic.ValidationError as error:
        assert MARKER in str(error)
        record = logging.LogRecord(
            "uvicorn.error",
            logging.ERROR,
            __file__,
            1,
            "Exception in ASGI application",
            None,
            sys.exc_info(),
        )

    line = json.loads(JsonFormatter().format(record))

    assert line["error_type"] == "ValidationError"
    assert "test_logs.py" in line["stack"][0]
    assert MARKER not in json.dumps(line, ensure_ascii=False)
