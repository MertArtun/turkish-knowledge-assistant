from fastapi.testclient import TestClient

from app.contracts import ReadinessResponse
from app.main import create_app
from app.settings import load_settings
from tests.fake_assistant import make_assistant


def test_live_reports_running_process():
    client = TestClient(create_app(make_assistant()))

    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "live"}


def test_ready_reports_the_loaded_index_and_the_run_metadata():
    # create_app only exists once the corpus, model and index are loaded, so it is ready.
    client = TestClient(create_app(make_assistant(settings=load_settings({"TOP_K": "5"}))))

    response = client.get("/health/ready")

    assert response.status_code == 200
    readiness = ReadinessResponse.model_validate(response.json())
    assert readiness.status == "ready"
    assert readiness.checks.corpus_index is True
    assert readiness.checks.embedding_model is True
    metadata = readiness.run_metadata
    assert metadata.app_mode == "evidence_only"
    assert metadata.generation_configured is False
    assert metadata.top_k == 5
    assert metadata.min_retrieval_score is None
    assert metadata.embedding_model == "intfloat/multilingual-e5-small"
    assert metadata.embedding_revision == "614241f622f53c4eeff9890bdc4f31cfecc418b3"
    assert metadata.corpus_fingerprint == "test-fingerprint"
    assert metadata.prompt_hash is None


def test_ready_reports_generation_availability_without_leaking_the_key():
    key = "test-key-value-that-must-never-be-echoed"
    settings = load_settings({"OPENAI_API_KEY": key})
    client = TestClient(create_app(make_assistant(settings=settings)))

    response = client.get("/health/ready")

    assert response.json()["run_metadata"]["generation_configured"] is True
    assert key not in response.text
