"""
Testes unitários para error handlers RFC 7807 (Problem Details).

Verifica que erros 404 e 422 seguem o formato:
  {"type", "title", "status", "detail"}
"""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client() -> TestClient:
    from src.api.main import app
    return TestClient(app)


class TestErrorHandlers:
    def test_404_follows_rfc7807(self, client: TestClient) -> None:
        response = client.get("/rota-que-nao-existe")
        assert response.status_code == 404
        body = response.json()
        assert "type" in body
        assert "title" in body
        assert "status" in body
        assert "detail" in body
        assert body["status"] == 404

    def test_422_on_invalid_input(self, client: TestClient) -> None:
        # Endpoint que espera JSON inválido → 422
        response = client.post(
            "/api/v1/jobs",
            json={},  # prompt obrigatório ausente
        )
        assert response.status_code == 422
        body = response.json()
        assert "type" in body
        assert "status" in body
        assert body["status"] == 422

    def test_404_status_field_is_integer(self, client: TestClient) -> None:
        response = client.get("/nao-existe")
        assert isinstance(response.json()["status"], int)

    def test_error_type_is_string(self, client: TestClient) -> None:
        response = client.get("/nao-existe")
        assert isinstance(response.json()["type"], str)
