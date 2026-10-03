import asyncio
import socket
import threading
from datetime import UTC, date, datetime

import pytest

from app.contracts import AskRequest, AskResponse, DocumentVersion, ExcludedVersion, Scope
from app.service import AskError
from app.settings import load_settings
from tests.fake_assistant import CHUNKS, CORPUS, QueryEmbedder, make_assistant

TR = Scope(country="TR", customer_type="B2B", product="MH-10")
DOCUMENTS = {doc.metadata.doc_id: doc.metadata for doc in CORPUS}


def ask(assistant, request_id: str = "req-1", **request) -> AskResponse:
    return asyncio.run(assistant.ask(AskRequest.model_validate(request), request_id))


def version(doc_id: str) -> DocumentVersion:
    meta = DOCUMENTS[doc_id]
    return DocumentVersion(
        doc_id=doc_id, version=meta.version, valid_from=meta.valid_from, valid_to=meta.valid_to
    )


def excluded(doc_id: str, reason: str) -> ExcludedVersion:
    return ExcludedVersion(**version(doc_id).model_dump(), reason=reason)


# --- evidence_only ------------------------------------------------------------------------------


def test_evidence_mode_returns_candidates_of_the_current_version_with_canonical_quotes():
    # The expired D03 section is the closest match; it must not appear, and must not push the
    # current D04 section out of the top 4 either.
    assistant = make_assistant(
        {
            "D03#kargo": 0.95,
            "D04#kargo": 0.90,
            "D05#kullanim": 0.80,
            "D04#sure": 0.70,
            "D05#bedel": 0.60,
        }
    )

    response = ask(assistant, question="  İade kargosunu kim ödüyor? ", as_of="2026-10-04")

    assert response.status == "evidence_only"
    assert response.mode == "evidence_only"
    assert (response.answer, response.claims, response.sources) == (None, [], [])
    assert (response.missing_topics, response.reason_code) == ([], None)
    assert response.request_id == "req-1"
    assert (response.effective_as_of, response.effective_scope) == (date(2026, 10, 4), TR)
    expected_ids = ["D04#kargo", "D05#kullanim", "D04#sure", "D05#bedel"]
    assert response.retrieved_chunk_ids == expected_ids
    assert [item.chunk_id for item in response.evidence] == expected_ids
    for item in response.evidence:
        chunk = CHUNKS[item.chunk_id]
        meta = DOCUMENTS[chunk.doc_id]
        # The quote is the stored section text, and the metadata comes from the document.
        assert item.quote == chunk.content
        assert (item.doc_id, item.section_id) == (chunk.doc_id, chunk.section_id)
        assert tuple(item.heading_path) == chunk.heading_path
        assert (item.document_title, item.version) == (meta.title, meta.version)
        assert (item.valid_from, item.valid_to) == (meta.valid_from, meta.valid_to)


def test_version_decisions_cover_only_the_retrieved_procedures_in_first_appearance_order():
    assistant = make_assistant(
        {"D04#kargo": 0.9, "D05#bedel": 0.8, "D04#sure": 0.7, "D08#saatler": 0.6}
    )

    response = ask(assistant, question="İade kargosunu kim ödüyor?", as_of="2026-10-04")

    assert [(d.procedure_id, d.selected, d.excluded) for d in response.version_decisions] == [
        ("returns", version("D04"), [excluded("D03", "expired")]),
        ("refund-payment", version("D05"), []),
        ("support-hours", version("D08"), []),
    ]


def test_historical_as_of_searches_the_old_version_and_reports_the_new_one_as_future():
    assistant = make_assistant({"D04#sure": 0.95, "D03#sure": 0.90})

    response = ask(assistant, question="1 Haziran 2026'da iade süresi neydi?", as_of="2026-06-01")

    assert response.retrieved_chunk_ids[0] == "D03#sure"
    assert not any(chunk_id.startswith("D04#") for chunk_id in response.retrieved_chunk_ids)
    returns = response.version_decisions[0]
    assert (returns.procedure_id, returns.selected) == ("returns", version("D03"))
    assert returns.excluded == [excluded("D04", "future_effective")]


def test_missing_as_of_means_today_in_istanbul_from_the_injected_clock():
    # 21:30 UTC on 30 June is already 1 July in Istanbul, the first day of D04.
    late_june = datetime(2026, 6, 30, 21, 30, tzinfo=UTC)
    assistant = make_assistant({"D03#sure": 0.95, "D04#sure": 0.90}, now=late_june)

    response = ask(assistant, question="İade süresi nedir?")

    assert response.effective_as_of == date(2026, 7, 1)
    assert response.retrieved_chunk_ids[0] == "D04#sure"


def test_query_is_embedded_once_with_the_e5_query_prefix():
    embedder = QueryEmbedder()

    ask(make_assistant(embedder=embedder), question="  Destek saatleri nedir? ")

    assert embedder.embedded_texts == ["query: Destek saatleri nedir?"]


# --- insufficient_evidence ----------------------------------------------------------------------


def test_unsupported_scope_is_insufficient_evidence_without_any_search_or_fallback():
    embedder = QueryEmbedder()
    germany = {"country": "DE", "customer_type": "B2B", "product": "MH-10"}

    response = ask(
        make_assistant({"D04#sure": 0.9}, embedder=embedder),
        question="Almanya'daki müşteriler de 30 günde iade edebilir mi?",
        scope=germany,
    )

    assert response.status == "insufficient_evidence"
    assert response.reason_code == "unsupported_scope"
    assert response.answer
    assert response.effective_scope == Scope(**germany)
    assert (response.evidence, response.retrieved_chunk_ids, response.version_decisions) == (
        [],
        [],
        [],
    )
    assert embedder.embedded_texts == []


def test_date_without_any_valid_version_is_insufficient_evidence_no_valid_version():
    embedder = QueryEmbedder()

    response = ask(
        make_assistant(embedder=embedder), question="İade süresi nedir?", as_of="2025-12-31"
    )

    assert response.status == "insufficient_evidence"
    assert response.reason_code == "no_valid_version"
    assert response.retrieved_chunk_ids == []
    assert embedder.embedded_texts == []


def test_threshold_that_removes_every_candidate_gives_not_in_documents():
    settings = load_settings({"MIN_RETRIEVAL_SCORE": "0.95"})
    assistant = make_assistant({"D04#sure": 0.9, "D01#baglanti": 0.5}, settings=settings)

    response = ask(assistant, question="MH-10'un garantisi kaç ay?")

    assert response.status == "insufficient_evidence"
    assert response.reason_code == "not_in_documents"
    assert (response.evidence, response.retrieved_chunk_ids) == ([], [])


# --- refused requests ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("environment", "request_mode"),
    [
        ({}, "generative"),
        ({"APP_MODE": "generative", "OPENAI_API_KEY": "test-key-not-real"}, None),
    ],
)
def test_generative_request_is_refused_as_not_configured_never_answered_with_evidence(
    environment, request_mode
):
    embedder = QueryEmbedder()
    assistant = make_assistant(
        {"D04#kargo": 0.9}, settings=load_settings(environment), embedder=embedder
    )

    with pytest.raises(AskError) as refused:
        ask(assistant, question="İade kargosunu kim ödüyor?", mode=request_mode)

    assert refused.value.code == "generation_not_configured"
    assert embedder.embedded_texts == []


def test_question_over_the_model_token_limit_is_invalid_not_truncated():
    embedder = QueryEmbedder(max_tokens=6)
    question = "bir iki üç dört beş altı yedi"

    with pytest.raises(AskError) as refused:
        ask(make_assistant(embedder=embedder), question=question)

    assert refused.value.code == "invalid_request"
    assert question not in refused.value.message
    assert embedder.embedded_texts == []


# --- execution ----------------------------------------------------------------------------------


def test_query_embedding_runs_off_the_event_loop_one_call_at_a_time():
    embedder = QueryEmbedder(delay_seconds=0.05)
    assistant = make_assistant({"D08#saatler": 0.9}, embedder=embedder)
    request = AskRequest(question="Destek saatleri nedir?")

    async def ask_three_while_counting_loop_ticks() -> int:
        ticks = 0

        async def heartbeat() -> None:
            nonlocal ticks
            while True:
                await asyncio.sleep(0.005)
                ticks += 1

        beating = asyncio.create_task(heartbeat())
        await asyncio.gather(*(assistant.ask(request, f"req-{n}") for n in range(3)))
        beating.cancel()
        return ticks

    ticks = asyncio.run(ask_three_while_counting_loop_ticks())

    # 3 x 50 ms of blocking work on the loop would leave the heartbeat almost no ticks.
    assert ticks >= 10
    assert threading.main_thread() not in embedder.threads
    assert embedder.max_concurrent_calls == 1


def test_evidence_mode_makes_no_network_call(monkeypatch):
    def refuse(*args, **kwargs):
        raise AssertionError("evidence_only must not open a network connection")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)

    response = ask(make_assistant({"D09#sifre": 0.9}), question="Parolamı unuttum, ne yapmalıyım?")

    assert response.status == "evidence_only"
