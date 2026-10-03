from fastapi.testclient import TestClient

from app.contracts import ReadinessResponse
from app.main import create_app
from app.settings import load_settings


def test_live_reports_running_process():
    client = TestClient(create_app(load_settings({})))

    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "live"}


def test_ready_is_503_until_index_and_embedding_exist():
    client = TestClient(create_app(load_settings({"TOP_K": "5"})))

    response = client.get("/health/ready")

    assert response.status_code == 503
    readiness = ReadinessResponse.model_validate(response.json())
    assert readiness.status == "not_ready"
    assert readiness.checks.corpus_index is False
    assert readiness.checks.embedding_model is False
    assert readiness.run_metadata.app_mode == "evidence_only"
    assert readiness.run_metadata.top_k == 5


def test_ready_reports_generation_availability_without_leaking_the_key():
    key = "test-key-value-that-must-never-be-echoed"
    client = TestClient(create_app(load_settings({"OPENAI_API_KEY": key})))

    response = client.get("/health/ready")

    assert response.json()["run_metadata"]["generation_configured"] is True
    assert key not in response.text
