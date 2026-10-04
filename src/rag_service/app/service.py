"""The request flow of the assistant, in one place.

resolve as_of and scope -> select the valid document versions -> search only those versions ->
evidence-only response, or a generated answer checked against the sections the model was given.
The corpus, the embedding model, the index and the generator are set up once at startup
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
    Claim,
    ErrorCode,
    Mode,
    ReasonCode,
    Scope,
    SourceSection,
    VersionDecision,
)
from app.documents import Chunk, Document, load_corpus
from app.embeddings import E5Embedder, Embedder, embed_query, query_text
from app.generation import (
    Generation,
    GenerationError,
    Generator,
    OpenAIGenerator,
    SystemPrompt,
    compose_answer,
    load_system_prompt,
    render_input,
    validate_answer,
)
from app.index_store import Index, load_or_build_index
from app.retrieval import ScoredChunk, retrieve
from app.settings import Settings
from app.versioning import Clock, effective_as_of, effective_scope, select_versions, system_clock

logger = logging.getLogger(__name__)

# The most sections the model sees, whatever TOP_K is. Each section is at most 512 embedding-model
# tokens (checked when the index loads) and so is the question, which bounds the model's input.
GENERATION_SECTION_LIMIT = 4

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
GENERATION_FAILED: dict[ErrorCode, str] = {
    "provider_unavailable": (
        "Dil modeli sağlayıcısı isteği şu anda karşılayamıyor. Biraz sonra tekrar deneyin."
    ),
    "generation_timeout": "Dil modeli zamanında cevap vermedi.",
    "invalid_generation_output": (
        "Dil modelinin cevabı kaynak doğrulamasından geçmedi; güvenilir bir cevap üretilemedi."
    ),
}


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
    # None without OPENAI_API_KEY: generative requests are then refused, never answered otherwise.
    generator: Generator | None = None
    prompt: SystemPrompt = field(default_factory=load_system_prompt)

    async def ask(self, request: AskRequest, request_id: str) -> AskResponse:
        started = time.perf_counter()
        as_of = effective_as_of(request.as_of, self.clock)
        scope = effective_scope(request.scope)
        mode = request.mode or self.settings.app_mode
        if mode == "generative" and self.generator is None:
            # No silent fallback: a generative request never receives evidence it did not ask for.
            raise AskError("generation_not_configured", GENERATION_NOT_CONFIGURED)

        decisions = select_versions([doc.metadata for doc in self.documents], scope, as_of)
        if not any(decision.selected for decision in decisions.values()):
            reason = _reason_without_valid_version(decisions)
            message = NO_DOCUMENTS_FOR_SCOPE if reason == "unsupported_scope" else NO_VALID_VERSION
            self._log(request_id, mode, reason, [], started, embed_ms=0.0, search_ms=0.0)
            return _insufficient(request_id, mode, as_of, scope, reason, message)

        embedding_started = time.perf_counter()
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
        embed_ms = (embedded - embedding_started) * 1000
        if not results:
            # Only possible with MIN_RETRIEVAL_SCORE set: every candidate scored below it.
            self._log(request_id, mode, "not_in_documents", [], started, embed_ms, search_ms)
            return _insufficient(
                request_id, mode, as_of, scope, "not_in_documents", NO_MATCHING_SECTION
            )

        if mode == "generative":
            return await self._generate(
                request_id,
                request.question,
                as_of,
                scope,
                results,
                decisions,
                started,
                embed_ms,
                search_ms,
            )

        self._log(request_id, mode, "evidence_only", results, started, embed_ms, search_ms)
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
            evidence=[self._source_section(result.chunk) for result in results],
            missing_topics=[],
            reason_code=None,
            version_decisions=self._decisions_for(results, decisions),
            retrieved_chunk_ids=[result.chunk.chunk_id for result in results],
        )

    async def _generate(
        self,
        request_id: str,
        question: str,
        as_of: date,
        scope: Scope,
        results: list[ScoredChunk],
        decisions: dict[str, VersionDecision],
        started: float,
        embed_ms: float,
        search_ms: float,
    ) -> AskResponse:
        # Only these sections reach the model: current versions, in this scope, at most four.
        provided = {r.chunk.chunk_id: r.chunk for r in results[:GENERATION_SECTION_LIMIT]}
        user_input = render_input(question, as_of, scope, list(provided.values()))
        prompt_id = f"{self.prompt.version}@{self.prompt.sha256[:12]}"
        generation_started = time.perf_counter()
        try:
            generation = await self._call_model(user_input)
            validate_answer(generation.answer, provided)
        except GenerationError as error:
            self._log(request_id, "generative", error.code, results, started, embed_ms, search_ms)
            # The detail names status codes, schema error types or source IDs; never the
            # provider's message (it can echo part of the key) or the model's text.
            logger.info(
                "generation",
                extra={
                    "fields": {
                        "request_id": request_id,
                        "outcome": error.code,
                        "detail": error.detail,
                        "prompt": prompt_id,
                        "generate_ms": _milliseconds_since(generation_started),
                    }
                },
            )
            raise AskError(error.code, GENERATION_FAILED[error.code]) from None
        generate_ms = _milliseconds_since(generation_started)

        answer = generation.answer
        cited = list(dict.fromkeys(i for claim in answer.claims for i in claim.source_chunk_ids))
        self._log(request_id, "generative", answer.status, results, started, embed_ms, search_ms)
        logger.info(
            "generation",
            extra={
                "fields": {
                    "request_id": request_id,
                    "outcome": answer.status,
                    "cited": cited,
                    "reason_code": answer.reason_code,
                    "missing_topics": len(answer.missing_topics),
                    # As reported by the provider, which may differ from OPENAI_MODEL.
                    "model": generation.model,
                    "prompt": prompt_id,
                    "generate_ms": generate_ms,
                    "input_tokens": generation.input_tokens,
                    "output_tokens": generation.output_tokens,
                    "reasoning_tokens": generation.reasoning_tokens,
                }
            },
        )
        return AskResponse(
            request_id=request_id,
            status=answer.status,
            mode="generative",
            effective_as_of=as_of,
            effective_scope=scope,
            answer=compose_answer(answer),
            claims=[Claim(text=c.text, source_chunk_ids=c.source_chunk_ids) for c in answer.claims],
            # Title, version, dates and the verbatim quote come from the corpus, never the model.
            sources=[self._source_section(provided[chunk_id]) for chunk_id in cited],
            evidence=[],
            missing_topics=answer.missing_topics,
            reason_code=answer.reason_code,
            version_decisions=self._decisions_for(results, decisions),
            retrieved_chunk_ids=[result.chunk.chunk_id for result in results],
        )

    async def _call_model(self, user_input: str) -> Generation:
        # The SDK's timeout applies to each connect/read/write phase, so a slowly trickling reply
        # could outlast it. This deadline bounds the whole call and keeps it well inside the .NET
        # API's longer upstream timeout, so a slow model is reported as generation_timeout.
        try:
            with anyio.fail_after(self.settings.llm_timeout_seconds):
                return await self.generator.generate(self.prompt.text, user_input)
        except TimeoutError:
            raise GenerationError(
                "generation_timeout", "LLM_TIMEOUT_SECONDS passed for the whole call"
            ) from None

    def _embed_question(self, question: str) -> np.ndarray:
        """Blocking; runs in a worker thread. A question is never truncated to fit the model."""
        if self.embedder.count_tokens(query_text(question)) > self.embedder.max_tokens:
            raise AskError("invalid_request", QUESTION_TOO_LONG)
        return embed_query(self.embedder, question)

    def _source_section(self, chunk: Chunk) -> SourceSection:
        # Quote and metadata come from the loaded corpus, so they are always the stored text of
        # the selected version.
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
        started: float,
        embed_ms: float,
        search_ms: float,
    ) -> None:
        # Scores and timings belong in logs, not in the response; the question text never does.
        used = (self._document(result.chunk.doc_id).metadata for result in results)
        logger.info(
            "ask",
            extra={
                "fields": {
                    "request_id": request_id,
                    "mode": mode,
                    "outcome": outcome,
                    "retrieved": [
                        {"chunk_id": r.chunk.chunk_id, "score": round(r.score, 4)} for r in results
                    ],
                    # The document versions the retrieved sections come from.
                    "versions": list(
                        dict.fromkeys(f"{meta.doc_id}@{meta.version}" for meta in used)
                    ),
                    "embed_ms": round(embed_ms, 1),
                    "search_ms": round(search_ms, 1),
                    "total_ms": _milliseconds_since(started),
                    "corpus": self.index.fingerprint[:12],
                }
            },
        )


def load_assistant(settings: Settings) -> Assistant:
    """Startup: any CorpusError, model download error or IndexStoreError stops the service.

    The generator is created whenever a key is set (no network call), so a generative request can
    be served in either APP_MODE; without a key it stays None."""
    documents = load_corpus(settings.knowledge_dir)
    embedder = E5Embedder(
        settings.embedding_model, settings.embedding_revision, settings.model_cache_dir
    )
    index = load_or_build_index(documents, embedder, settings.index_path)
    generator = OpenAIGenerator(settings) if settings.openai_api_key is not None else None
    return Assistant(
        settings=settings, documents=documents, embedder=embedder, index=index, generator=generator
    )


def _milliseconds_since(started: float) -> float:
    return round((time.perf_counter() - started) * 1000, 1)


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
