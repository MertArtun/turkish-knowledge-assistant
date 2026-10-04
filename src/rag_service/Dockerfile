# RAG service. Build from the repository root: docker build -f src/rag_service/Dockerfile .
# CPU only: embeddings run on ONNX Runtime; there is no PyTorch or CUDA in uv.lock.
# Same interpreter as .python-version and the tests.
FROM python:3.12.12-slim-trixie

# Unprivileged user. It owns the mount points of the two writable volumes, so a new named volume
# starts with that ownership. The home directory holds Hugging Face's download scratch files.
RUN useradd --create-home --uid 10001 app \
    && mkdir -p /var/lib/rag/index /var/lib/rag/models \
    && chown app:app /var/lib/rag/index /var/lib/rag/models

WORKDIR /app
ENV PATH="/app/.venv/bin:$PATH" \
    UV_PYTHON_DOWNLOADS=never

# Exactly the locked dependencies, without dev tools. uv is mounted for this step only.
COPY src/rag_service/pyproject.toml src/rag_service/uv.lock src/rag_service/.python-version ./
RUN --mount=from=ghcr.io/astral-sh/uv:0.9.2,source=/uv,target=/bin/uv \
    uv sync --locked --no-dev --no-cache

COPY src/rag_service/app ./app
COPY src/rag_service/log_config.json ./

# Container paths; compose.yaml mounts the corpus read-only and the two volumes here.
ENV KNOWLEDGE_DIR=/knowledge \
    INDEX_PATH=/var/lib/rag/index/index.sqlite3 \
    MODEL_CACHE_DIR=/var/lib/rag/models

USER app
EXPOSE 8000
CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", \
     "--log-config", "log_config.json"]
