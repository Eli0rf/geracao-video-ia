"""
Testes de integração — valida que a aplicação FastAPI inicializa corretamente.
"""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client() -> TestClient:
    from src.api.main import app
    return TestClient(app)


class TestApiStartup:
    def test_openapi_schema_available(self, client: TestClient) -> None:
        response = client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert "openapi" in schema
        assert "info" in schema

    def test_docs_available(self, client: TestClient) -> None:
        response = client.get("/docs")
        assert response.status_code == 200

    def test_api_v1_prefix_exists(self, client: TestClient) -> None:
        """Qualquer rota em /api/v1/ deve existir (não 404 de prefixo)."""
        # O endpoint /api/v1/jobs vai existir — 422 (sem body) é esperado, não 404
        response = client.post("/api/v1/jobs", json={})
        assert response.status_code != 404
