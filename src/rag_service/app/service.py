"""The request flow of the assistant, in one place.

resolve as_of and scope -> select the valid document versions -> search only those versions ->
build the response. The corpus, the embedding model and the index are loaded once at startup
(load_assistant); `Assistant.ask` only reads them.
"""

import logging
import time
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date

import anyio
import numpy as np

from app.contracts import (
    AskRequest,
    AskResponse,
    ErrorCode,
    Mode,
    ReasonCode,
    Scope,
    SourceSection,
    VersionDecision,
)
from app.documents import Document, load_corpus
from app.embeddings import E5Embedder, Embedder, embed_query, query_text
from app.index_store import Index, load_or_build_index
from app.retrieval import ScoredChunk, retrieve
from app.settings import Settings
from app.versioning import Clock, effective_as_of, effective_scope, select_versions, system_clock

logger = logging.getLogger(__name__)

# Standard explanations written by the server, never by a model. They state why nothing can be
# answered from the documents; they contain no policy values.
NO_DOCUMENTS_FOR_SCOPE = (
    "İstenen kapsam için onaylı belge bulunmuyor. Başka bir kapsamın belgeleri bu kapsama "
    "uygulanmaz."
)
NO_VALID_VERSION = "İstenen tarihte bu kapsam için geçerli onaylı belge sürümü bulunmuyor."
NO_MATCHING_SECTION = "Onaylı belgelerde bu soruyla eşleşen bir bölüm bulunamadı."
QUESTION_TOO_LONG = (
    "Soru, arama modelinin işleyebileceği uzunluğu aşıyor; soruyu kısaltıp tekrar deneyin."
)
GENERATION_NOT_CONFIGURED = (
    "Üretken cevap modu bu ortamda yapılandırılmamış. mode alanını evidence_only olarak "
    "gönderebilirsiniz."
)


class AskError(Exception):
    """A request the service refuses. `code` is the contract's error.code; `message` is safe."""

    def __init__(self, code: ErrorCode, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class Assistant:
    settings: Settings
    documents: Sequence[Document]
    embedder: Embedder
    index: Index
    clock: Clock = system_clock
    # The model already spreads one call over all CPU cores, so query embeddings run one at a
    # time in a worker thread: the event loop stays free and parallel calls cannot oversubscribe
    # the CPU.
    embedding_slot: anyio.CapacityLimiter = field(default_factory=lambda: anyio.CapacityLimiter(1))

    async def ask(self, request: AskRequest, request_id: str) -> AskResponse:
        as_of = effective_as_of(request.as_of, self.clock)
        scope = effective_scope(request.scope)
        mode = request.mode or self.settings.app_mode
        if mode == "generative":
            # Grounded generation is not part of this build. Refusing keeps a generative request
            # from receiving unvalidated text, or evidence it did not ask for (no fallback).
            raise AskError("generation_not_configured", GENERATION_NOT_CONFIGURED)

        decisions = select_versions([doc.metadata for doc in self.documents], scope, as_of)
        if not any(decision.selected for decision in decisions.values()):
            reason = _reason_without_valid_version(decisions)
            message = NO_DOCUMENTS_FOR_SCOPE if reason == "unsupported_scope" else NO_VALID_VERSION
            self._log(request_id, mode, reason, [], embed_ms=0.0, search_ms=0.0)
            return _insufficient(request_id, mode, as_of, scope, reason, message)

        started = time.perf_counter()
        query_vector = await anyio.to_thread.run_sync(
            self._embed_question, request.question, limiter=self.embedding_slot
        )
        embedded = time.perf_counter()
        results = retrieve(
            self.index,
            query_vector,
            decisions,
            top_k=self.settings.top_k,
            min_score=self.settings.min_retrieval_score,
        )
        search_ms = (time.perf_counter() - embedded) * 1000
        embed_ms = (embedded - started) * 1000
        if not results:
            # Only possible with MIN_RETRIEVAL_SCORE set: every candidate scored below it.
            self._log(request_id, mode, "not_in_documents", [], embed_ms, search_ms)
            return _insufficient(
                request_id, mode, as_of, scope, "not_in_documents", NO_MATCHING_SECTION
            )

        self._log(request_id, mode, "evidence_only", results, embed_ms, search_ms)
        return AskResponse(
            request_id=request_id,
            status="evidence_only",
            mode=mode,
            effective_as_of=as_of,
            effective_scope=scope,
            answer=None,
            claims=[],
            sources=[],
            # Candidates, not an answer: nothing says they answer the question.
            evidence=[self._source_section(result) for result in results],
            missing_topics=[],
            reason_code=None,
            version_decisions=self._decisions_for(results, decisions),
            retrieved_chunk_ids=[result.chunk.chunk_id for result in results],
        )

    def _embed_question(self, question: str) -> np.ndarray:
        """Blocking; runs in a worker thread. A question is never truncated to fit the model."""
        if self.embedder.count_tokens(query_text(question)) > self.embedder.max_tokens:
            raise AskError("invalid_request", QUESTION_TOO_LONG)
        return embed_query(self.embedder, question)

    def _source_section(self, result: ScoredChunk) -> SourceSection:
        # Quote and metadata come from the loaded corpus, so they are always the stored text of
        # the selected version.
        chunk = result.chunk
        meta = self._document(chunk.doc_id).metadata
        return SourceSection(
            chunk_id=chunk.chunk_id,
            doc_id=chunk.doc_id,
            document_title=meta.title,
            version=meta.version,
            section_id=chunk.section_id,
            heading_path=list(chunk.heading_path),
            quote=chunk.content,
            valid_from=meta.valid_from,
            valid_to=meta.valid_to,
        )

    def _decisions_for(
        self, results: list[ScoredChunk], decisions: dict[str, VersionDecision]
    ) -> list[VersionDecision]:
        """Decisions of the retrieved procedures only, in the order they first appear."""
        procedures = dict.fromkeys(
            self._document(result.chunk.doc_id).metadata.procedure_id for result in results
        )
        return [decisions[procedure_id] for procedure_id in procedures]

    def _document(self, doc_id: str) -> Document:
        return next(doc for doc in self.documents if doc.metadata.doc_id == doc_id)

    def _log(
        self,
        request_id: str,
        mode: Mode,
        outcome: str,
        results: list[ScoredChunk],
        embed_ms: float,
        search_ms: float,
    ) -> None:
        # Scores and timings belong in logs, not in the response; the question text never does.
        retrieved = ",".join(f"{r.chunk.chunk_id}:{r.score:.4f}" for r in results) or "-"
        logger.info(
            "ask request_id=%s mode=%s outcome=%s retrieved=%s embed_ms=%.1f search_ms=%.1f "
            "corpus=%s",
            request_id,
            mode,
            outcome,
            retrieved,
            embed_ms,
            search_ms,
            self.index.fingerprint[:12],
        )


def load_assistant(settings: Settings) -> Assistant:
    """Startup: any CorpusError, model download error or IndexStoreError stops the service."""
    documents = load_corpus(settings.knowledge_dir)
    embedder = E5Embedder(
        settings.embedding_model, settings.embedding_revision, settings.model_cache_dir
    )
    index = load_or_build_index(documents, embedder, settings.index_path)
    return Assistant(settings=settings, documents=documents, embedder=embedder, index=index)


def _reason_without_valid_version(decisions: dict[str, VersionDecision]) -> ReasonCode:
    """unsupported_scope when no document has the requested scope; otherwise no valid version."""
    reasons = {excluded.reason for decision in decisions.values() for excluded in decision.excluded}
    return "unsupported_scope" if reasons == {"scope_mismatch"} else "no_valid_version"


def _insufficient(
    request_id: str,
    mode: Mode,
    as_of: date,
    scope: Scope,
    reason: ReasonCode,
    message: str,
) -> AskResponse:
    return AskResponse(
        request_id=request_id,
        status="insufficient_evidence",
        mode=mode,
        effective_as_of=as_of,
        effective_scope=scope,
        answer=message,
        claims=[],
        sources=[],
        evidence=[],
        missing_topics=[],
        reason_code=reason,
        version_decisions=[],
        retrieved_chunk_ids=[],
    )
