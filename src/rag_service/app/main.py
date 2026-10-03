"""FastAPI entry point. Run with: uv run uvicorn app.main:create_app --factory"""

import os

from fastapi import FastAPI, Response, status

from app.contracts import ReadinessChecks, ReadinessResponse, RunMetadata
from app.settings import Settings, load_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    # Loading here (not at import time) keeps config errors out of test imports and makes
    # an invalid environment stop the process before it serves anything.
    settings = settings or load_settings(os.environ)
    app = FastAPI(title="rag-service")

    @app.get("/health/live")
    def live() -> dict[str, str]:
        return {"status": "live"}

    @app.get("/health/ready")
    def ready(response: Response) -> ReadinessResponse:
        # Corpus index and embedding model do not exist yet, so the service is never ready.
        checks = ReadinessChecks(corpus_index=False, embedding_model=False)
        is_ready = checks.corpus_index and checks.embedding_model
        if not is_ready:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return ReadinessResponse(
            status="ready" if is_ready else "not_ready",
            checks=checks,
            run_metadata=RunMetadata(
                app_mode=settings.app_mode,
                generation_configured=settings.generation_configured,
                llm_model=settings.openai_model,
                embedding_model=settings.embedding_model,
                embedding_revision=None,
                corpus_fingerprint=None,
                prompt_hash=None,
                top_k=settings.top_k,
                min_retrieval_score=settings.min_retrieval_score,
            ),
        )

    return app
