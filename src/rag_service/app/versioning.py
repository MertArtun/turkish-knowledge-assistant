"""Deterministic, server-side choice of the document version that may answer a request.

Rules (docs/project-spec.md §4): exact scope match, approved only, valid_from <= as_of < valid_to,
at most one valid version per (procedure_id, scope). Retrieval searches only the selected
documents, so an excluded version can never reach the answer, whatever its similarity score.
"""

from collections.abc import Callable, Iterable
from datetime import UTC, date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from app.contracts import DocumentVersion, ExcludedVersion, ExclusionReason, Scope, VersionDecision
from app.documents import CorpusError, DocumentMetadata

ISTANBUL = ZoneInfo("Europe/Istanbul")
# The scope of the fictional corpus. Only a request without a scope gets it; a request for any
# other scope is never answered from these documents.
DEFAULT_SCOPE = Scope(country="TR", customer_type="B2B", product="MH-10")

Clock = Callable[[], datetime]


def system_clock() -> datetime:
    return datetime.now(UTC)


def effective_as_of(requested: date | None, clock: Clock = system_clock) -> date:
    """The requested date, or today in Istanbul. `clock` must return a timezone-aware datetime."""
    if requested is not None:
        return requested
    return clock().astimezone(ISTANBUL).date()


def effective_scope(requested: Scope | None) -> Scope:
    return DEFAULT_SCOPE if requested is None else requested


def select_versions(
    documents: Iterable[DocumentMetadata], scope: Scope, as_of: date
) -> dict[str, VersionDecision]:
    """One decision per procedure in the corpus, keyed by procedure_id.

    Documents are processed in doc_id order, so the result never depends on file or input order.
    """
    by_procedure: dict[str, list[DocumentMetadata]] = {}
    for meta in sorted(documents, key=lambda doc: doc.doc_id):
        by_procedure.setdefault(meta.procedure_id, []).append(meta)
    return {
        procedure_id: _decide(procedure_id, versions, scope, as_of)
        for procedure_id, versions in by_procedure.items()
    }


def _decide(
    procedure_id: str, versions: list[DocumentMetadata], scope: Scope, as_of: date
) -> VersionDecision:
    valid: list[DocumentMetadata] = []
    excluded: list[ExcludedVersion] = []
    for meta in versions:
        reason = _exclusion_reason(meta, scope, as_of)
        if reason is None:
            valid.append(meta)
        else:
            excluded.append(ExcludedVersion(**_version_fields(meta), reason=reason))
    if len(valid) > 1:
        # load_corpus already rejects overlapping approved versions. If this is ever reached,
        # picking by order, version number or recency would hide a corpus error, so it fails.
        doc_ids = ", ".join(meta.doc_id for meta in valid)
        raise CorpusError(f"{procedure_id} has more than one valid version on {as_of}: {doc_ids}")
    selected = DocumentVersion(**_version_fields(valid[0])) if valid else None
    return VersionDecision(procedure_id=procedure_id, selected=selected, excluded=excluded)


def _exclusion_reason(meta: DocumentMetadata, scope: Scope, as_of: date) -> ExclusionReason | None:
    # Checked in the order of the selection rules; the first failing rule is the reported reason.
    if meta.scope != scope:
        return "scope_mismatch"
    if meta.status != "approved":
        return "not_approved"
    if as_of < meta.valid_from:
        return "future_effective"
    if meta.valid_to is not None and as_of >= meta.valid_to:
        return "expired"
    return None


def _version_fields(meta: DocumentMetadata) -> dict[str, Any]:
    return {
        "doc_id": meta.doc_id,
        "version": meta.version,
        "valid_from": meta.valid_from,
        "valid_to": meta.valid_to,
    }
