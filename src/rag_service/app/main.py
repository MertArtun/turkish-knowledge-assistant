"""FastAPI entry point. Run with: uv run uvicorn app.main:create_app --factory"""

import logging
import os
import re
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.contracts import (
    AskRequest,
    AskResponse,
    ErrorCode,
    ErrorDetail,
    ErrorResponse,
    ReadinessChecks,
    ReadinessResponse,
    RunMetadata,
)
from app.service import AskError, Assistant, load_assistant
from app.settings import load_settings

logger = logging.getLogger(__name__)

REQUEST_ID_HEADER = "X-Request-ID"
# The same rule as the .NET API. Used with fullmatch: `$` would also accept a trailing newline.
SAFE_REQUEST_ID = re.compile(r"[A-Za-z0-9._-]{1,64}")

# HTTP status of each error this service returns. The .NET API decides its own status from the
# code, so these matter only to direct callers.
ERROR_STATUS: dict[ErrorCode, int] = {
    "invalid_request": 400,
    "generation_not_configured": 503,
    "provider_unavailable": 503,
    "generation_timeout": 504,
    "invalid_generation_output": 502,
    "internal_error": 500,
}
INVALID_REQUEST_MESSAGE = (
    "İstek geçersiz. Kabul edilen alanlar: question (1–2000 karakter), as_of (YYYY-MM-DD), "
    "scope (country, customer_type, product; her biri 1–64 karakter) ve mode "
    "(generative | evidence_only)."
)
INTERNAL_ERROR_MESSAGE = "Beklenmeyen bir hata oluştu."


def create_app(assistant: Assistant | None = None) -> FastAPI:
    # Settings, corpus, model and index are loaded here, before uvicorn accepts connections; any
    # failure stops the process, so a running service has already passed every startup check.
    # Tests pass an assistant built with fakes.
    assistant = assistant or load_assistant(load_settings(os.environ))
    settings = assistant.settings
    readiness = ReadinessResponse(
        status="ready",
        checks=ReadinessChecks(corpus_index=True, embedding_model=True),
        run_metadata=RunMetadata(
            app_mode=settings.app_mode,
            # A generator exists only with a key; readiness never calls the paid model, so this
            # does not prove the key, quota or model access works.
            generation_configured=assistant.generator is not None,
            llm_model=settings.openai_model,
            embedding_model=settings.embedding_model,
            embedding_revision=settings.embedding_revision,
            corpus_fingerprint=assistant.index.fingerprint,
            prompt_version=assistant.prompt.version,
            prompt_hash=assistant.prompt.sha256,
            top_k=settings.top_k,
            min_retrieval_score=settings.min_retrieval_score,
        ),
    )
    app = FastAPI(title="rag-service")

    @app.middleware("http")
    async def assign_request_id(request: Request, call_next):
        request.state.request_id = accepted_request_id(request.headers.getlist(REQUEST_ID_HEADER))
        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request.state.request_id
        return response

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request: Request, error: RequestValidationError) -> JSONResponse:
        # FastAPI's default is 422 with the offending input echoed back; the contract is 400 with
        # a fixed message that never repeats the user's input. The log names fields, not values.
        fields = sorted({".".join(map(str, detail["loc"])) for detail in error.errors()})
        logger.info("invalid request request_id=%s fields=%s", request.state.request_id, fields)
        return error_response(request, "invalid_request", INVALID_REQUEST_MESSAGE)

    @app.exception_handler(AskError)
    async def refused(request: Request, error: AskError) -> JSONResponse:
        logger.info("refused request_id=%s code=%s", request.state.request_id, error.code)
        return error_response(request, error.code, error.message)

    @app.exception_handler(Exception)
    async def unexpected(request: Request, error: Exception) -> JSONResponse:
        # Starlette re-raises the exception after this response, so its traceback is logged;
        # the caller only gets the code.
        return error_response(request, "internal_error", INTERNAL_ERROR_MESSAGE)

    @app.get("/health/live")
    def live() -> dict[str, str]:
        return {"status": "live"}

    @app.get("/health/ready")
    def ready() -> ReadinessResponse:
        return readiness

    @app.post("/internal/ask")
    async def internal_ask(body: AskRequest, request: Request) -> AskResponse:
        return await assistant.ask(body, request.state.request_id)

    return app


def accepted_request_id(values: list[str]) -> str:
    """The caller's ID if it is exactly one safe token; otherwise a new one."""
    if len(values) == 1 and SAFE_REQUEST_ID.fullmatch(values[0]):
        return values[0]
    return uuid.uuid4().hex


def error_response(request: Request, code: ErrorCode, message: str) -> JSONResponse:
    request_id = request.state.request_id
    body = ErrorResponse(request_id=request_id, error=ErrorDetail(code=code, message=message))
    return JSONResponse(
        body.model_dump(mode="json"),
        status_code=ERROR_STATUS[code],
        # Set here too: the 500 handler runs outside the request ID middleware.
        headers={REQUEST_ID_HEADER: request_id},
    )
