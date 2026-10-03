"""Wire contract of the RAG service.

The .NET API exposes the same JSON shape; tests/contracts/*.json fixtures pin it for both sides.
"""

import re
from datetime import date
from typing import Annotated, Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

Mode = Literal["generative", "evidence_only"]
AnswerStatus = Literal["answered", "partial", "insufficient_evidence", "evidence_only"]
ReasonCode = Literal["not_in_documents", "unsupported_scope", "as_of_required", "no_valid_version"]
ExclusionReason = Literal["expired", "future_effective", "not_approved", "scope_mismatch"]
ErrorCode = Literal[
    "invalid_request",
    "payload_too_large",
    "service_not_ready",
    "generation_not_configured",
    "provider_unavailable",
    "generation_timeout",
    "invalid_generation_output",
    "upstream_unavailable",
    "upstream_timeout",
    "upstream_invalid_response",
    "internal_error",
]

ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


class ContractModel(BaseModel):
    # Unknown fields fail loudly so that drift between C# and Python breaks a fixture test.
    model_config = ConfigDict(extra="forbid")


class Scope(ContractModel):
    country: str = Field(min_length=1, max_length=64)
    customer_type: str = Field(min_length=1, max_length=64)
    product: str = Field(min_length=1, max_length=64)


class AskRequest(ContractModel):
    question: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)
    ]
    as_of: date | None = None
    scope: Scope | None = None
    mode: Mode | None = None

    @field_validator("as_of", mode="before")
    @classmethod
    def _plain_iso_date(cls, value: Any) -> Any:
        # Pydantic's lax date parsing also accepts midnight datetimes and unix timestamps; the
        # contract only allows YYYY-MM-DD so that C# DateOnly and Python date agree.
        if value is None or isinstance(value, date):
            return value
        if not isinstance(value, str) or not ISO_DATE.fullmatch(value):
            raise ValueError("as_of must be an ISO date (YYYY-MM-DD)")
        return value


class Claim(ContractModel):
    text: str = Field(min_length=1)
    source_chunk_ids: list[str] = Field(min_length=1)


class SourceSection(ContractModel):
    chunk_id: str
    doc_id: str
    document_title: str
    version: str
    section_id: str
    heading_path: list[str]
    quote: str
    valid_from: date
    valid_to: date | None


class DocumentVersion(ContractModel):
    doc_id: str
    version: str
    valid_from: date
    valid_to: date | None


class ExcludedVersion(DocumentVersion):
    reason: ExclusionReason


class VersionDecision(ContractModel):
    procedure_id: str
    selected: DocumentVersion | None
    excluded: list[ExcludedVersion]


class AskResponse(ContractModel):
    request_id: str
    status: AnswerStatus
    mode: Mode
    effective_as_of: date
    effective_scope: Scope
    answer: str | None
    claims: list[Claim]
    sources: list[SourceSection]
    evidence: list[SourceSection]
    missing_topics: list[str]
    reason_code: ReasonCode | None
    version_decisions: list[VersionDecision]
    retrieved_chunk_ids: list[str]

    @model_validator(mode="after")
    def _status_matches_content(self) -> "AskResponse":
        # The single definition of what each status promises. A violation is a server bug.
        cited_ids = {chunk_id for claim in self.claims for chunk_id in claim.source_chunk_ids}
        _require(
            cited_ids == {source.chunk_id for source in self.sources},
            "sources must be exactly the sections cited by claims",
        )
        has_claims = bool(self.claims)
        has_answer = bool(self.answer)
        if self.status == "answered":
            _require(
                has_claims and has_answer and not self.missing_topics,
                "answered needs claims, an answer and no missing_topics",
            )
        elif self.status == "partial":
            _require(
                has_claims and has_answer and bool(self.missing_topics),
                "partial needs claims, an answer and missing_topics",
            )
        elif self.status == "insufficient_evidence":
            _require(
                not has_claims and has_answer and self.reason_code is not None,
                "insufficient_evidence needs no claims, an explanation and a reason_code",
            )
        else:
            _require(
                not has_claims and self.answer is None and bool(self.evidence),
                "evidence_only needs evidence and no answer or claims",
            )
        _require(
            not self.evidence or self.status == "evidence_only",
            "evidence is only returned with status evidence_only",
        )
        _require(
            self.mode == "generative" or self.status in ("evidence_only", "insufficient_evidence"),
            "evidence_only mode never returns generated claims",
        )
        _require(
            self.mode == "evidence_only" or self.status != "evidence_only",
            "status evidence_only requires mode evidence_only",
        )
        return self


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


class ErrorDetail(ContractModel):
    code: ErrorCode
    message: str = Field(min_length=1)


class ErrorResponse(ContractModel):
    request_id: str
    error: ErrorDetail


class ReadinessChecks(ContractModel):
    corpus_index: bool
    embedding_model: bool


class RunMetadata(ContractModel):
    """Non-secret settings that identify a run; the eval runner records them via /health/ready."""

    app_mode: Mode
    generation_configured: bool
    llm_model: str
    embedding_model: str
    embedding_revision: str | None
    corpus_fingerprint: str | None
    prompt_hash: str | None
    top_k: int
    min_retrieval_score: float | None


class ReadinessResponse(ContractModel):
    status: Literal["ready", "not_ready"]
    checks: ReadinessChecks
    run_metadata: RunMetadata
