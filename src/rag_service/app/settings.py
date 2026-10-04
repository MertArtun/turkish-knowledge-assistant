"""Service configuration, read from environment variables and validated once at startup."""

from collections.abc import Mapping
from pathlib import Path

from pydantic import (
    AnyHttpUrl,
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    ValidationError,
    model_validator,
)

from app.contracts import Mode

# Environment variable name -> Settings field. These names are the public configuration
# contract and must match .env.example and the README.
ENV_TO_FIELD = {
    "APP_MODE": "app_mode",
    "OPENAI_API_KEY": "openai_api_key",
    "OPENAI_BASE_URL": "openai_base_url",
    "OPENAI_MODEL": "openai_model",
    "EMBEDDING_MODEL": "embedding_model",
    "EMBEDDING_REVISION": "embedding_revision",
    "KNOWLEDGE_DIR": "knowledge_dir",
    "INDEX_PATH": "index_path",
    "MODEL_CACHE_DIR": "model_cache_dir",
    "TOP_K": "top_k",
    "MIN_RETRIEVAL_SCORE": "min_retrieval_score",
    "LLM_TIMEOUT_SECONDS": "llm_timeout_seconds",
}
FIELD_TO_ENV = {field: env for env, field in ENV_TO_FIELD.items()}


class ConfigError(Exception):
    """Invalid startup configuration. The message names variables, never their values."""


class Settings(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    app_mode: Mode = "evidence_only"
    openai_api_key: SecretStr | None = None
    # OpenAI by default; OpenRouter's OpenAI-compatible endpoint is https://openrouter.ai/api/v1.
    openai_base_url: AnyHttpUrl = AnyHttpUrl("https://api.openai.com/v1")
    # The model ID as the endpoint expects it (OpenRouter prefixes it with "openai/"). It must be
    # a reasoning model: the request sets a reasoning effort.
    openai_model: str = Field(default="gpt-6-luna", min_length=1)
    embedding_model: str = Field(default="intfloat/multilingual-e5-small", min_length=1)
    # Hugging Face commit of the model repo, checked against the HF API when it was pinned. A full
    # hash (not a branch) keeps the model fixed and lets a cached copy load without the network.
    # A different revision needs `uv run pytest -m model` and measure_retrieval.py rerun.
    embedding_revision: str = Field(
        default="614241f622f53c4eeff9890bdc4f31cfecc418b3", pattern=r"^[0-9a-f]{40}$"
    )
    # Relative paths resolve against the working directory; commands run from src/rag_service.
    knowledge_dir: Path = Path("../../data/knowledge")
    index_path: Path = Path("../../var/index.sqlite3")
    model_cache_dir: Path = Path("../../var/models")
    top_k: int = Field(default=4, ge=1, le=20)
    # Disabled until a threshold is measured on development questions (cosine range is -1..1).
    min_retrieval_score: float | None = Field(default=None, ge=-1.0, le=1.0)
    llm_timeout_seconds: float = Field(default=25.0, gt=0, le=120)

    @model_validator(mode="after")
    def _generative_mode_requires_key(self) -> "Settings":
        if self.app_mode == "generative" and self.openai_api_key is None:
            raise ValueError("APP_MODE=generative requires OPENAI_API_KEY")
        return self


def load_settings(environ: Mapping[str, str]) -> Settings:
    # Blank values (e.g. `OPENAI_API_KEY=` copied from .env.example) mean "not set". Surrounding
    # whitespace is stripped: a stray space in a copied key would otherwise break authentication.
    values = {
        field: environ[env].strip()
        for env, field in ENV_TO_FIELD.items()
        if environ.get(env, "").strip()
    }
    try:
        return Settings(**values)
    except ValidationError as error:
        problems = "; ".join(
            f"{_env_name(detail['loc'])}: {detail['msg']}"
            for detail in error.errors(
                include_url=False, include_context=False, include_input=False
            )
        )
        # `from None`: the chained pydantic error would print raw inputs, including the key.
        raise ConfigError(f"Invalid configuration: {problems}") from None


def _env_name(location: tuple[int | str, ...]) -> str:
    if not location:
        return "configuration"
    return FIELD_TO_ENV.get(str(location[0]), str(location[0]))
