from pathlib import Path

import pytest

from app.settings import ENV_TO_FIELD, ConfigError, load_settings

FAKE_KEY = "test-key-value-that-must-never-be-echoed"


def test_defaults_start_in_evidence_only_mode_without_key():
    settings = load_settings({})

    assert settings.app_mode == "evidence_only"
    assert settings.openai_api_key is None
    assert settings.generation_configured is False
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
            "OPENAI_MODEL": "some-model",
            "TOP_K": "6",
            "MIN_RETRIEVAL_SCORE": "0.35",
            "LLM_TIMEOUT_SECONDS": "10.5",
            "KNOWLEDGE_DIR": "/srv/knowledge",
        }
    )

    assert settings.app_mode == "generative"
    assert settings.generation_configured is True
    assert settings.openai_model == "some-model"
    assert settings.top_k == 6
    assert settings.min_retrieval_score == 0.35
    assert settings.llm_timeout_seconds == 10.5
    assert str(settings.knowledge_dir) == "/srv/knowledge"


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
        ("TOP_K", "four"),
        ("MIN_RETRIEVAL_SCORE", "1.5"),
        ("LLM_TIMEOUT_SECONDS", "0"),
        ("LLM_TIMEOUT_SECONDS", "3600"),
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


def test_env_example_lists_exactly_the_configuration_names():
    env_example = Path(__file__).resolve().parents[3] / ".env.example"
    entries = dict(
        line.split("=", 1)
        for line in env_example.read_text(encoding="utf-8").splitlines()
        if line and not line.startswith("#")
    )
    dotnet_only = {"RAG_SERVICE_URL", "RAG_TIMEOUT_SECONDS"}

    assert set(entries) - dotnet_only == set(ENV_TO_FIELD)
    assert load_settings(entries).app_mode == "evidence_only"
