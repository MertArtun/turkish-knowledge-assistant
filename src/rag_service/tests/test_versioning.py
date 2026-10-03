import json
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from app.contracts import AskResponse, DocumentVersion, ExcludedVersion, Scope, VersionDecision
from app.documents import CorpusError, DocumentMetadata, load_corpus
from app.versioning import DEFAULT_SCOPE, effective_as_of, effective_scope, select_versions
from tests.corpus_files import KNOWLEDGE_DIR, write_doc

TR = Scope(country="TR", customer_type="B2B", product="MH-10")
DE = Scope(country="DE", customer_type="B2B", product="MH-10")
FIXTURE_DIR = Path(__file__).resolve().parents[3] / "tests" / "contracts"


def real_metadata() -> list[DocumentMetadata]:
    return [doc.metadata for doc in load_corpus(KNOWLEDGE_DIR)]


def meta(doc_id: str, version: str, **fields) -> DocumentMetadata:
    values = {
        "procedure_id": "returns",
        "title": "İade Prosedürü",
        "valid_from": date(2026, 1, 1),
        "valid_to": None,
        "status": "approved",
        "scope": TR,
        "supersedes": None,
        **fields,
    }
    return DocumentMetadata(doc_id=doc_id, version=version, **values)


def version_of(m: DocumentMetadata) -> DocumentVersion:
    return DocumentVersion(
        doc_id=m.doc_id, version=m.version, valid_from=m.valid_from, valid_to=m.valid_to
    )


def excluded(m: DocumentMetadata, reason: str) -> ExcludedVersion:
    return ExcludedVersion(**version_of(m).model_dump(), reason=reason)


# --- Real corpus boundaries ----------------------------------------------------------------

D03 = DocumentVersion(
    doc_id="D03", version="1.0", valid_from=date(2026, 1, 1), valid_to=date(2026, 7, 1)
)
D04 = DocumentVersion(doc_id="D04", version="2.0", valid_from=date(2026, 7, 1), valid_to=None)


@pytest.mark.parametrize(
    ("as_of", "selected", "excluded_version", "reason"),
    [
        # D04 supersedes D03, but on 2026-06-30 only D03 is valid: supersedes never decides.
        (date(2026, 6, 30), D03, D04, "future_effective"),
        # valid_to is exclusive: D03 is no longer valid on the day D04 starts.
        (date(2026, 7, 1), D04, D03, "expired"),
        (date(2026, 10, 4), D04, D03, "expired"),
    ],
)
def test_returns_version_follows_the_validity_boundaries(as_of, selected, excluded_version, reason):
    decision = select_versions(real_metadata(), TR, as_of)["returns"]

    assert decision == VersionDecision(
        procedure_id="returns",
        selected=selected,
        excluded=[ExcludedVersion(**excluded_version.model_dump(), reason=reason)],
    )


def test_every_procedure_has_exactly_one_current_document_on_2026_10_04():
    decisions = select_versions(real_metadata(), TR, date(2026, 10, 4))

    assert {d.procedure_id: d.selected.doc_id for d in decisions.values()} == {
        "mh10-setup": "D01",
        "audio-troubleshooting": "D02",
        "returns": "D04",
        "refund-payment": "D05",
        "support-ticket": "D06",
        "priority-sla": "D07",
        "support-hours": "D08",
        "account-access": "D09",
        "safe-support-sharing": "D10",
    }


def test_date_before_every_version_selects_nothing_instead_of_the_nearest_document():
    decisions = select_versions(real_metadata(), TR, date(2025, 12, 31))

    assert all(decision.selected is None for decision in decisions.values())
    assert [(e.doc_id, e.reason) for e in decisions["returns"].excluded] == [
        ("D03", "future_effective"),
        ("D04", "future_effective"),
    ]


def test_other_country_gets_no_fallback_to_the_turkish_documents():
    decisions = select_versions(real_metadata(), DE, date(2026, 10, 4))

    assert all(decision.selected is None for decision in decisions.values())
    assert {e.reason for d in decisions.values() for e in d.excluded} == {"scope_mismatch"}


@pytest.mark.parametrize("name", ["answered", "partial", "insufficient-evidence", "evidence-only"])
def test_contract_fixture_version_decisions_match_the_real_corpus(name):
    raw = json.loads((FIXTURE_DIR / f"ask-response-{name}.json").read_text(encoding="utf-8"))
    response = AskResponse.model_validate(raw)

    decisions = select_versions(real_metadata(), response.effective_scope, response.effective_as_of)

    for fixture_decision in response.version_decisions:
        assert decisions[fixture_decision.procedure_id] == fixture_decision


# --- Selection rules -----------------------------------------------------------------------


def test_gap_between_versions_selects_nothing():
    v1 = meta("D01", "1.0", valid_to=date(2026, 3, 1))
    v2 = meta("D02", "2.0", valid_from=date(2026, 4, 1))

    decision = select_versions([v1, v2], TR, date(2026, 3, 15))["returns"]

    assert decision.selected is None
    assert decision.excluded == [excluded(v1, "expired"), excluded(v2, "future_effective")]


def test_draft_and_withdrawn_versions_are_never_selected_even_with_a_higher_version():
    current = meta("D01", "2.0", valid_from=date(2026, 7, 1))
    draft = meta("D02", "3.0", valid_from=date(2026, 8, 1), status="draft", supersedes="D01")
    withdrawn = meta("D03", "4.0", valid_from=date(2026, 9, 1), status="withdrawn")

    decision = select_versions([current, draft, withdrawn], TR, date(2026, 10, 4))["returns"]

    assert decision.selected == version_of(current)
    assert decision.excluded == [
        excluded(draft, "not_approved"),
        excluded(withdrawn, "not_approved"),
    ]


def test_exclusion_reason_follows_the_order_scope_then_status_then_dates():
    # Each document fails several checks; the reported reason is the first failing check.
    other_scope_draft = meta("D01", "1.0", scope=DE, status="draft", valid_to=date(2026, 2, 1))
    future_draft = meta("D02", "2.0", status="draft", valid_from=date(2027, 1, 1))

    decision = select_versions([other_scope_draft, future_draft], TR, date(2026, 10, 4))["returns"]

    assert [(e.doc_id, e.reason) for e in decision.excluded] == [
        ("D01", "scope_mismatch"),
        ("D02", "not_approved"),
    ]


def test_result_does_not_depend_on_input_order():
    documents = real_metadata()

    forward = select_versions(documents, TR, date(2026, 10, 4))
    backward = select_versions(list(reversed(documents)), TR, date(2026, 10, 4))

    assert list(forward.items()) == list(backward.items())


def test_two_valid_approved_versions_are_an_error_not_a_choice():
    # load_corpus rejects this; selection must not silently pick one if it ever sees it.
    first = meta("D01", "1.0")
    second = meta("D02", "2.0", valid_from=date(2026, 7, 1))

    with pytest.raises(CorpusError, match="returns has more than one valid version on 2026-10-04"):
        select_versions([first, second], TR, date(2026, 10, 4))


# --- Adding a v3 (load-time rules and selection together) ----------------------------------


def write_v1_and_v2(directory: Path, v2_valid_to: date | None) -> None:
    write_doc(directory, "03-returns-v1.md", doc_id="D03", valid_to=date(2026, 7, 1))
    write_doc(
        directory,
        "04-returns-v2.md",
        doc_id="D04",
        version="2.0",
        valid_from=date(2026, 7, 1),
        valid_to=v2_valid_to,
        supersedes="D03",
    )


def test_v3_next_to_an_open_ended_v2_is_rejected(tmp_path):
    write_v1_and_v2(tmp_path, v2_valid_to=None)
    write_doc(
        tmp_path,
        "11-returns-v3.md",
        doc_id="D11",
        version="3.0",
        valid_from=date(2027, 1, 1),
        supersedes="D04",
    )

    with pytest.raises(CorpusError, match="approved versions D04 and D11 of returns overlap"):
        load_corpus(tmp_path)


def test_closed_v2_and_future_v3_are_accepted_and_v3_waits_for_its_start_date(tmp_path):
    write_v1_and_v2(tmp_path, v2_valid_to=date(2027, 1, 1))
    write_doc(
        tmp_path,
        "11-returns-v3.md",
        doc_id="D11",
        version="3.0",
        valid_from=date(2027, 1, 1),
        supersedes="D04",
    )
    documents = [doc.metadata for doc in load_corpus(tmp_path)]

    today = select_versions(documents, TR, date(2026, 10, 4))["returns"]
    later = select_versions(documents, TR, date(2027, 1, 1))["returns"]

    assert (today.selected.doc_id, [(e.doc_id, e.reason) for e in today.excluded]) == (
        "D04",
        [("D03", "expired"), ("D11", "future_effective")],
    )
    assert (later.selected.doc_id, [(e.doc_id, e.reason) for e in later.excluded]) == (
        "D11",
        [("D03", "expired"), ("D04", "expired")],
    )


# --- Effective request values --------------------------------------------------------------


def fixed_clock(moment: datetime):
    return lambda: moment


@pytest.mark.parametrize(
    ("now_utc", "istanbul_today"),
    [
        (datetime(2026, 10, 3, 20, 59, tzinfo=UTC), date(2026, 10, 3)),
        # 21:00 UTC is already midnight in Istanbul (UTC+3).
        (datetime(2026, 10, 3, 21, 0, tzinfo=UTC), date(2026, 10, 4)),
    ],
)
def test_missing_as_of_means_today_in_istanbul(now_utc, istanbul_today):
    assert effective_as_of(None, clock=fixed_clock(now_utc)) == istanbul_today


def test_explicit_as_of_is_used_as_given():
    clock = fixed_clock(datetime(2026, 10, 4, 9, 0, tzinfo=UTC))

    assert effective_as_of(date(2026, 6, 1), clock=clock) == date(2026, 6, 1)


def test_missing_scope_means_the_fictional_default_scope():
    assert effective_scope(None) == DEFAULT_SCOPE == TR
    assert effective_scope(DE) == DE
