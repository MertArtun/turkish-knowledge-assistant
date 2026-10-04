from pathlib import Path

import pytest
from pydantic import ValidationError

from app.settings import ENV_TO_FIELD, ConfigError, Settings, load_settings

FAKE_KEY = "test-key-value-that-must-never-be-echoed"


def test_defaults_start_in_evidence_only_mode_without_key():
    settings = load_settings({})

    assert settings.app_mode == "evidence_only"
    assert settings.openai_api_key is None
    assert str(settings.openai_base_url) == "https://api.openai.com/v1"
    assert settings.openai_model == "gpt-6-luna"
    assert settings.top_k == 4
    assert settings.min_retrieval_score is None
    assert settings.llm_timeout_seconds == 25


def test_empty_values_copied_from_env_example_mean_unset():
    settings = load_settings({"OPENAI_API_KEY": "", "MIN_RETRIEVAL_SCORE": "  ", "TOP_K": ""})

    assert settings.openai_api_key is None
    assert settings.min_retrieval_score is None
    assert settings.top_k == 4


def test_environment_values_are_parsed():
    settings = load_settings(
        {
            "APP_MODE": "generative",
            "OPENAI_API_KEY": FAKE_KEY,
            "OPENAI_BASE_URL": "https://openrouter.ai/api/v1",
            "OPENAI_MODEL": "some-model",
            "EMBEDDING_REVISION": "0123456789abcdef0123456789abcdef01234567",
            "TOP_K": "6",
            "MIN_RETRIEVAL_SCORE": "0.35",
            "LLM_TIMEOUT_SECONDS": "10.5",
            "KNOWLEDGE_DIR": "/srv/knowledge",
        }
    )

    assert settings.app_mode == "generative"
    assert settings.openai_api_key.get_secret_value() == FAKE_KEY
    assert settings.openai_base_url.host == "openrouter.ai"
    assert settings.openai_model == "some-model"
    assert settings.embedding_revision == "0123456789abcdef0123456789abcdef01234567"
    assert settings.top_k == 6
    assert settings.min_retrieval_score == 0.35
    assert settings.llm_timeout_seconds == 10.5
    assert str(settings.knowledge_dir) == "/srv/knowledge"


def test_embedding_revision_defaults_to_the_pinned_model_commit():
    assert load_settings({}).embedding_revision == "614241f622f53c4eeff9890bdc4f31cfecc418b3"


@pytest.mark.parametrize("value", ["main", "614241f", "614241F622F53C4EEFF9890BDC4F31CFECC418B3"])
def test_embedding_revision_must_be_a_full_commit_hash(value):
    # A branch name or short hash would let the model change underneath an unchanged config.
    with pytest.raises(ValidationError, match="embedding_revision"):
        Settings(embedding_revision=value)


def test_surrounding_whitespace_is_stripped_from_the_key():
    # A stray space copied into .env would otherwise break authentication.
    settings = load_settings({"OPENAI_API_KEY": f"  {FAKE_KEY} \n"})

    assert settings.openai_api_key.get_secret_value() == FAKE_KEY


def test_generative_mode_without_key_is_a_config_error():
    with pytest.raises(ConfigError, match="OPENAI_API_KEY"):
        load_settings({"APP_MODE": "generative"})


def test_unknown_app_mode_is_rejected():
    with pytest.raises(ConfigError, match="APP_MODE"):
        load_settings({"APP_MODE": "chat"})


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("TOP_K", "0"),
        ("TOP_K", "100"),
        # TOP_K is also the number of sections the model reads; 8 bounds that context.
        ("TOP_K", "9"),
        ("TOP_K", "four"),
        ("MIN_RETRIEVAL_SCORE", "1.5"),
        ("LLM_TIMEOUT_SECONDS", "0"),
        ("LLM_TIMEOUT_SECONDS", "3600"),
        ("OPENAI_BASE_URL", "openrouter.ai/api/v1"),
        ("OPENAI_BASE_URL", "ftp://openrouter.ai/api/v1"),
        ("EMBEDDING_REVISION", "main"),
    ],
)
def test_out_of_range_values_are_rejected_with_the_variable_name(name, value):
    with pytest.raises(ConfigError, match=name):
        load_settings({name: value})


def test_config_error_never_contains_the_key_value():
    with pytest.raises(ConfigError) as caught:
        load_settings({"APP_MODE": "generative", "OPENAI_API_KEY": FAKE_KEY, "TOP_K": "zero"})

    assert FAKE_KEY not in str(caught.value)
    # A chained pydantic error would print the raw input (including the key) in tracebacks.
    assert caught.value.__suppress_context__ is True


def test_key_is_not_exposed_by_settings_repr():
    settings = load_settings({"OPENAI_API_KEY": FAKE_KEY})

    assert FAKE_KEY not in repr(settings)


def env_example_entries() -> dict[str, str]:
    env_example = Path(__file__).resolve().parents[3] / ".env.example"
    return dict(
        line.split("=", 1)
        for line in env_example.read_text(encoding="utf-8").splitlines()
        if line and not line.startswith("#")
    )


def test_env_example_lists_exactly_the_configuration_names():
    entries = env_example_entries()
    dotnet_only = {"RAG_SERVICE_URL", "RAG_TIMEOUT_SECONDS"}

    assert set(entries) - dotnet_only == set(ENV_TO_FIELD)
    assert load_settings(entries).app_mode == "evidence_only"


def test_env_example_gives_the_dotnet_upstream_more_time_than_the_llm_deadline():
    # Otherwise the .NET API gives up first: a slow model is reported as upstream_timeout
    # instead of generation_timeout, and the layer that failed is no longer visible.
    entries = env_example_entries()

    assert float(entries["RAG_TIMEOUT_SECONDS"]) > float(entries["LLM_TIMEOUT_SECONDS"])
