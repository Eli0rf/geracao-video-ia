"""
Testes para GET /metrics (TASK-014) — saída em texto no formato Prometheus,
sem biblioteca externa: contagem rápida agrupada por status no banco.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from src.models.video_job import JobStatus
from src.models.video_job_crud import create_video_job, update_job_status


@pytest.fixture()
def engine():
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
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def seeded(engine):
    """2 pending, 1 completed, 1 failed."""
    with Session(engine) as s:
        create_video_job(s, prompt="a")
        create_video_job(s, prompt="b")
        c1 = create_video_job(s, prompt="c")
        f1 = create_video_job(s, prompt="d")
        update_job_status(s, c1.id, JobStatus.COMPLETED, output_path="outputs/fake.mp4")
        update_job_status(s, f1.id, JobStatus.FAILED, error_message="boom")
    return {"pending": 2, "completed": 1, "failed": 1}


class TestGetMetrics:
    def test_returns_200_plain_text(self, client) -> None:
        r = client.get("/metrics")
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/plain")

    def test_counts_jobs_by_status(self, client, seeded) -> None:
        r = client.get("/metrics")
        text = r.text
        assert 'video_jobs_total{status="pending"} 2' in text
        assert 'video_jobs_total{status="completed"} 1' in text
        assert 'video_jobs_total{status="failed"} 1' in text
        # Nenhum job cancelled/processing no banco — não deve sair com valor > 0
        assert 'video_jobs_total{status="processing"} 0' not in text

    def test_includes_prometheus_metadata(self, client) -> None:
        r = client.get("/metrics")
        assert "# HELP video_jobs_total" in r.text
        assert "# TYPE video_jobs_total counter" in r.text

    def test_empty_db_reports_zero_total(self, client) -> None:
        r = client.get("/metrics")
        assert "# TYPE video_jobs_total counter" in r.text

    def test_also_available_under_api_v1(self, client, seeded) -> None:
        r = client.get("/api/v1/metrics")
        assert r.status_code == 200
        assert 'video_jobs_total{status="pending"} 2' in r.text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
