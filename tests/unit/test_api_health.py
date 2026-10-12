"""
Testes unitários para o endpoint GET /health.

Verifica status, versão e formato de resposta.
"""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client() -> TestClient:
    from src.api.main import app
    return TestClient(app)


class TestHealthEndpoint:
    def test_health_returns_200(self, client: TestClient) -> None:
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_returns_status_ok(self, client: TestClient) -> None:
        response = client.get("/health")
        assert response.json()["status"] == "ok"

    def test_health_returns_version(self, client: TestClient) -> None:
        response = client.get("/health")
        data = response.json()
        assert "version" in data
        assert isinstance(data["version"], str)
        assert len(data["version"]) > 0

    def test_health_returns_environment(self, client: TestClient) -> None:
        response = client.get("/health")
        assert "environment" in response.json()

    def test_health_content_type_is_json(self, client: TestClient) -> None:
        response = client.get("/health")
        assert "application/json" in response.headers["content-type"]
