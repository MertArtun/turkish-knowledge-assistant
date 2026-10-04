"""Grounded answer generation and the server-side checks of what the model returns.

The model receives only the question, the effective date and scope, and the sections selected for
this request, as JSON data. It returns a small structure (status, claims with source IDs, missing
topics, reason). The server checks that structure against this request's sections and writes the
final answer, titles, versions and quotes itself; the model never produces them.
"""

import hashlib
import json
import re
from collections.abc import Collection, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Literal, Protocol

import httpx2
import openai
import pydantic
from pydantic import BaseModel, ConfigDict

from app.contracts import ErrorCode, ReasonCode, Scope
from app.documents import Chunk
from app.settings import Settings

PROMPT_PATH = Path(__file__).parent / "prompts" / "answer.txt"
# Bump together with the prompt text; tests pin the hash of each version.
PROMPT_VERSION = "answer-v3"
# Reasoning tokens count against this budget too; the effort is kept low (see generate()).
MAX_OUTPUT_TOKENS = 1000
OPENROUTER_HOST = "openrouter.ai"
# Sent only through OpenRouter: serve the request from OpenAI itself (never another host of the
# model), without silent fallbacks, and only where every parameter (structured output, store,
# reasoning) is supported.
OPENROUTER_ROUTING = {
    "provider": {"only": ["openai"], "allow_fallbacks": False, "require_parameters": True}
}

# Written by the server, never by the model. An insufficient answer has no claims, so its text is
# the explanation of its reason code.
INSUFFICIENT_ANSWER: dict[ReasonCode, str] = {
    "not_in_documents": "Onaylı belgelerde bu soruyu yanıtlayacak bilgi bulunamadı.",
    "unsupported_scope": (
        "Belgeler yalnızca isteğin kapsamı için geçerlidir; soruda geçen başka bir kapsama "
        "uygulanamaz."
    ),
    "as_of_required": (
        "Soru, isteğin tarihinden (as_of) farklı bir tarihi soruyor; o tarihteki kural için isteği "
        "o tarihle gönderin."
    ),
}
MISSING_TOPICS_SENTENCE = "Bu istekteki belgelerle yanıtlanamayan konular: {}."


class ModelClaim(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str
    source_chunk_ids: list[str]


class ModelAnswer(BaseModel):
    """The structured output the model must return. Deliberately without constraints such as
    minItems: the rules are checked by validate_answer, so a violation is reported, not hidden in
    a schema the provider may or may not enforce."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["answered", "partial", "insufficient_evidence"]
    claims: list[ModelClaim]
    missing_topics: list[str]
    reason_code: Literal["not_in_documents", "unsupported_scope", "as_of_required"] | None


@dataclass(frozen=True)
class SystemPrompt:
    version: str
    text: str
    sha256: str


def load_system_prompt() -> SystemPrompt:
    raw = PROMPT_PATH.read_bytes()
    return SystemPrompt(
        version=PROMPT_VERSION, text=raw.decode("utf-8"), sha256=hashlib.sha256(raw).hexdigest()
    )


@dataclass(frozen=True)
class Generation:
    answer: ModelAnswer
    # As reported by the provider, for logs; None when it reports nothing.
    model: str | None
    input_tokens: int | None
    output_tokens: int | None
    reasoning_tokens: int | None = None


class GenerationError(Exception):
    """A generation that cannot be used. `code` is the contract's error.code; `detail` is for the
    log only and never contains the key, the question or the provider's message."""

    def __init__(self, code: ErrorCode, detail: str):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


class Generator(Protocol):
    """The one seam to the language model; tests replace it with a fake."""

    async def generate(self, instructions: str, user_input: str) -> Generation: ...


def render_input(question: str, as_of: date, scope: Scope, chunks: Sequence[Chunk]) -> str:
    """The user message: JSON data only. JSON string escaping keeps a question or a document from
    closing its field and passing itself off as instructions or another source."""
    data = {
        "effective_as_of": as_of.isoformat(),
        "effective_scope": scope.model_dump(),
        "question": question,
        "sources": [
            {"id": chunk.chunk_id, "heading_path": list(chunk.heading_path), "text": chunk.content}
            for chunk in chunks
        ],
    }
    return json.dumps(data, ensure_ascii=False, indent=2)


class OpenAIGenerator:
    """The real generator: OpenAI's Responses API through the official SDK, directly or through
    OpenRouter (OPENAI_BASE_URL)."""

    def __init__(self, settings: Settings, http_client: httpx2.AsyncClient | None = None):
        if settings.openai_api_key is None:
            raise ValueError("OpenAIGenerator needs OPENAI_API_KEY")
        self.model = settings.openai_model
        # Key and URL are always passed explicitly, so the SDK never falls back to reading the
        # environment itself. One attempt: retries would multiply the time and cost budget.
        self.client = openai.AsyncOpenAI(
            api_key=settings.openai_api_key.get_secret_value(),
            base_url=str(settings.openai_base_url),
            timeout=settings.llm_timeout_seconds,
            max_retries=0,
            http_client=http_client,
        )
        self.extra_body = (
            OPENROUTER_ROUTING if settings.openai_base_url.host == OPENROUTER_HOST else None
        )

    async def generate(self, instructions: str, user_input: str) -> Generation:
        try:
            response = await self.client.responses.parse(
                model=self.model,
                instructions=instructions,
                input=user_input,
                text_format=ModelAnswer,
                # The provider is asked not to keep the response; this does not switch off its own
                # (or an intermediary's) retention policies.
                store=False,
                max_output_tokens=MAX_OUTPUT_TOKENS,
                # A reasoning model; a low effort keeps reasoning tokens inside the output budget
                # and the call inside the timeout. No temperature: the model does not accept it.
                reasoning={"effort": "low"},
                extra_body=self.extra_body,
            )
        except openai.APITimeoutError:
            raise GenerationError("generation_timeout", "provider call timed out") from None
        except openai.APIConnectionError:
            raise GenerationError("provider_unavailable", "connection failed") from None
        except openai.APIStatusError as error:
            # The provider's message is not logged: it can echo part of the key. OpenRouter's
            # routing refusals (e.g. a data policy excluding every allowed endpoint) carry short
            # reason slugs, which are logged instead.
            detail = f"status={error.status_code} code={_label(error.code)!r}"
            if reasons := _routing_refusal_reasons(error.body):
                detail += f" routing={reasons!r}"
            raise GenerationError("provider_unavailable", detail) from None
        except pydantic.ValidationError as error:
            # Not JSON, cut off, or not the requested schema.
            kinds = sorted({item["type"] for item in error.errors()})
            raise GenerationError("invalid_generation_output", f"unparseable: {kinds}") from None

        if response.status != "completed":
            reason = response.incomplete_details.reason if response.incomplete_details else None
            detail = f"response status={_label(response.status)!r} reason={_label(reason)!r}"
            raise GenerationError("invalid_generation_output", detail)
        if any(
            content.type == "refusal"
            for item in response.output
            if item.type == "message"
            for content in item.content
        ):
            raise GenerationError("invalid_generation_output", "model refused")
        if response.output_parsed is None:
            raise GenerationError("invalid_generation_output", "no structured output")

        usage = response.usage
        return Generation(
            answer=response.output_parsed,
            model=response.model,
            input_tokens=usage.input_tokens if usage else None,
            output_tokens=usage.output_tokens if usage else None,
            reasoning_tokens=usage.output_tokens_details.reasoning_tokens if usage else None,
        )


def _routing_refusal_reasons(body: object) -> list[str]:
    metadata = body.get("metadata") if isinstance(body, dict) else None
    reasons = metadata.get("ineligibility_reasons") if isinstance(metadata, dict) else None
    if not isinstance(reasons, list):
        return []
    return [_label(item.get("reason")) for item in reasons if isinstance(item, dict)]


# Provider codes and reasons are free text from outside; only identifier-like values are logged.
SAFE_LABEL = re.compile(r"[A-Za-z0-9_.:-]{1,64}")


def _label(value: object) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if SAFE_LABEL.fullmatch(text) else "unrecognized"


def validate_answer(answer: ModelAnswer, provided_ids: Collection[str]) -> None:
    """Every rule the server enforces on the model's output. A violation is reported as
    invalid_generation_output; nothing is dropped or repaired to make the answer pass."""
    problems = []
    for number, claim in enumerate(answer.claims, start=1):
        if not claim.text.strip():
            problems.append(f"claim {number} is blank")
        if not claim.source_chunk_ids:
            problems.append(f"claim {number} has no source")
        # A real corpus section that was not given to the model for this request is as
        # unverifiable as an invented one.
        # The IDs themselves are model output and stay out of the log; their count is enough.
        foreign = [chunk_id for chunk_id in claim.source_chunk_ids if chunk_id not in provided_ids]
        if foreign:
            problems.append(f"claim {number} cites {len(foreign)} source(s) not provided")
    if any(not topic.strip() for topic in answer.missing_topics):
        problems.append("blank missing topic")

    has_claims, has_missing = bool(answer.claims), bool(answer.missing_topics)
    if answer.status == "answered" and not (
        has_claims and not has_missing and answer.reason_code is None
    ):
        problems.append("answered needs claims, no missing topics and no reason_code")
    if answer.status == "partial" and not (has_claims and has_missing):
        problems.append("partial needs claims and missing topics")
    if answer.status == "insufficient_evidence" and (has_claims or answer.reason_code is None):
        problems.append("insufficient_evidence needs no claims and a reason_code")

    if problems:
        raise GenerationError("invalid_generation_output", "; ".join(problems))


def compose_answer(answer: ModelAnswer) -> str:
    """The final answer: the validated claims (or the standard explanation of an insufficient
    answer), then the standard sentence naming what could not be answered."""
    if answer.status == "insufficient_evidence":
        sentences = [INSUFFICIENT_ANSWER[answer.reason_code]]
    else:
        sentences = [claim.text for claim in answer.claims]
    if answer.missing_topics:
        # Only the sentence's punctuation is adjusted; missing_topics itself stays as returned.
        topics = "; ".join(topic.strip().rstrip(".") for topic in answer.missing_topics)
        sentences.append(MISSING_TOPICS_SENTENCE.format(topics))
    return " ".join(sentences)
