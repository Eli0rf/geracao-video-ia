"""tests/integration/test_frontend.py — Bloco 5 (TASK-021): frontend estático.

Verifica que o mount de `static/` em `/` serve a interface pixel art
e que o catch-all NÃO sombreia as rotas da API (/api/v1/*) nem /health.
"""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client() -> TestClient:
    from src.api.main import app

    return TestClient(app)


def test_root_serves_pixel_art_homepage(client: TestClient) -> None:
    resp = client.get("/")
    assert resp.status_code == 200
    assert "GAME STUDIO" in resp.text
    assert "Press+Start+2P" in resp.text
    assert "text/html" in resp.headers["content-type"]


def test_frontend_static_assets(client: TestClient) -> None:
    css = client.get("/style.css")
    assert css.status_code == 200
    assert "text/css" in css.headers["content-type"]
    assert "--bg" in css.text  # variáveis do tema neon/retro

    js = client.get("/app.js")
    assert js.status_code == 200
    assert "api/v1/jobs" in js.text  # polling de status


def test_static_mount_does_not_shadow_api(client: TestClient) -> None:
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    jobs = client.get("/api/v1/jobs")
    assert jobs.status_code == 200
