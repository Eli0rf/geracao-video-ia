"""
Testes para o bloco E02 — todos os endpoints de jobs:
  POST   /api/v1/jobs
  GET    /api/v1/jobs/{id}
  GET    /api/v1/jobs
  GET    /api/v1/jobs/{id}/download
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from src.models.video_job import JobStatus


@pytest.fixture()
def engine():
    """Engine SQLite em memória com StaticPool — mesma conexão para todos."""
    e = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(e)
    return e


@pytest.fixture()
def client(engine):
    from src.api import deps
    from src.api.main import create_app

    def override():
        with Session(engine) as s:
            yield s

    app = create_app()
    app.dependency_overrides[deps.get_session] = override
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


# ── POST /api/v1/jobs ──────────────────────────────────────────────────────────

class TestPostJobs:
    def test_returns_202(self, client):
        r = client.post("/api/v1/jobs", json={"prompt": "a cat on the moon"})
        assert r.status_code == 202

    def test_returns_uuid(self, client):
        r = client.post("/api/v1/jobs", json={"prompt": "test"})
        assert len(r.json()["id"]) == 36

    def test_status_is_pending(self, client):
        r = client.post("/api/v1/jobs", json={"prompt": "test"})
        assert r.json()["status"] == JobStatus.PENDING

    def test_default_model(self, client):
        r = client.post("/api/v1/jobs", json={"prompt": "test"})
        assert r.json()["model"] == "animatediff"

    def test_custom_model(self, client):
        r = client.post("/api/v1/jobs", json={"prompt": "test", "model": "cogvideox"})
        assert r.status_code == 202
        assert r.json()["model"] == "cogvideox"

    def test_empty_prompt_422(self, client):
        r = client.post("/api/v1/jobs", json={"prompt": ""})
        assert r.status_code == 422

    def test_invalid_model_422(self, client):
        r = client.post("/api/v1/jobs", json={"prompt": "test", "model": "gpt-999"})
        assert r.status_code == 422

    def test_width_not_multiple_of_8_422(self, client):
        r = client.post("/api/v1/jobs", json={"prompt": "test", "width": 101})
        assert r.status_code == 422

    def test_height_not_multiple_of_8_422(self, client):
        r = client.post("/api/v1/jobs", json={"prompt": "test", "height": 99})
        assert r.status_code == 422

    def test_width_too_large_422(self, client):
        r = client.post("/api/v1/jobs", json={"prompt": "test", "width": 2000})
        assert r.status_code == 422

    def test_prompt_too_long_422(self, client):
        r = client.post("/api/v1/jobs", json={"prompt": "x" * 2001})
        assert r.status_code == 422

    def test_error_is_rfc7807(self, client):
        r = client.post("/api/v1/jobs", json={"prompt": ""})
        body = r.json()
        assert "type" in body and "status" in body and body["status"] == 422


# ── GET /api/v1/jobs/{id} ──────────────────────────────────────────────────────

class TestGetJob:
    def test_returns_200(self, client):
        job_id = client.post("/api/v1/jobs", json={"prompt": "find me"}).json()["id"]
        r = client.get(f"/api/v1/jobs/{job_id}")
        assert r.status_code == 200

    def test_returns_correct_prompt(self, client):
        job_id = client.post("/api/v1/jobs", json={"prompt": "hello"}).json()["id"]
        r = client.get(f"/api/v1/jobs/{job_id}")
        assert r.json()["prompt"] == "hello"

    def test_nonexistent_returns_404(self, client):
        r = client.get("/api/v1/jobs/00000000-0000-0000-0000-000000000000")
        assert r.status_code == 404

    def test_404_is_rfc7807(self, client):
        r = client.get("/api/v1/jobs/00000000-0000-0000-0000-000000000000")
        assert r.json()["status"] == 404

    def test_output_url_none_when_pending(self, client):
        job_id = client.post("/api/v1/jobs", json={"prompt": "test"}).json()["id"]
        r = client.get(f"/api/v1/jobs/{job_id}")
        assert r.json().get("output_url") is None

    def test_output_url_present_when_completed(self, client, engine):
        from src.models.video_job_crud import update_job_status
        job_id = client.post("/api/v1/jobs", json={"prompt": "test"}).json()["id"]
        with Session(engine) as s:
            update_job_status(s, job_id, JobStatus.COMPLETED, output_path="/outputs/abc.mp4")
        r = client.get(f"/api/v1/jobs/{job_id}")
        assert r.json()["output_url"] is not None


# ── GET /api/v1/jobs ───────────────────────────────────────────────────────────

class TestListJobs:
    def test_empty_returns_200(self, client):
        r = client.get("/api/v1/jobs")
        assert r.status_code == 200

    def test_empty_list_structure(self, client):
        r = client.get("/api/v1/jobs")
        body = r.json()
        assert body["items"] == []
        assert body["total"] == 0

    def test_lists_created_jobs(self, client):
        client.post("/api/v1/jobs", json={"prompt": "job1"})
        client.post("/api/v1/jobs", json={"prompt": "job2"})
        r = client.get("/api/v1/jobs")
        assert r.json()["total"] == 2

    def test_pagination_page_size(self, client):
        for i in range(5):
            client.post("/api/v1/jobs", json={"prompt": f"job{i}"})
        r = client.get("/api/v1/jobs?page=1&page_size=2")
        assert len(r.json()["items"]) == 2
        assert r.json()["total"] == 5

    def test_filter_by_status(self, client, engine):
        from src.models.video_job_crud import update_job_status
        j1 = client.post("/api/v1/jobs", json={"prompt": "p1"}).json()["id"]
        client.post("/api/v1/jobs", json={"prompt": "p2"})
        with Session(engine) as s:
            update_job_status(s, j1, JobStatus.COMPLETED)
        r = client.get("/api/v1/jobs?status=completed")
        assert r.json()["total"] == 1


# ── GET /api/v1/jobs/{id}/download ────────────────────────────────────────────

class TestDownloadJob:
    def test_pending_job_returns_409(self, client):
        job_id = client.post("/api/v1/jobs", json={"prompt": "test"}).json()["id"]
        r = client.get(f"/api/v1/jobs/{job_id}/download")
        assert r.status_code == 409

    def test_nonexistent_job_returns_404(self, client):
        r = client.get("/api/v1/jobs/00000000-0000-0000-0000-000000000000/download")
        assert r.status_code == 404

    def test_completed_job_missing_file_returns_410(self, client, engine, tmp_path):
        from src.models.video_job_crud import update_job_status
        job_id = client.post("/api/v1/jobs", json={"prompt": "test"}).json()["id"]
        with Session(engine) as s:
            update_job_status(
                s, job_id, JobStatus.COMPLETED,
                output_path=str(tmp_path / "missing.mp4"),
            )
        r = client.get(f"/api/v1/jobs/{job_id}/download")
        assert r.status_code == 410

    def test_completed_job_with_file_returns_200(self, client, engine, tmp_path):
        from src.models.video_job_crud import update_job_status
        video = tmp_path / "video.mp4"
        video.write_bytes(b"fake-mp4-content")
        job_id = client.post("/api/v1/jobs", json={"prompt": "test"}).json()["id"]
        with Session(engine) as s:
            update_job_status(
                s, job_id, JobStatus.COMPLETED,
                output_path=str(video),
            )
        r = client.get(f"/api/v1/jobs/{job_id}/download")
        assert r.status_code == 200
        assert "video" in r.headers["content-type"]
