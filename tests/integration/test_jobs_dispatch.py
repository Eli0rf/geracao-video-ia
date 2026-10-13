"""
Testes de integração — despacho de jobs para processamento em background (E05).

Sobrepõe `get_job_processor` com um `JobProcessor` real sobre um engine SQLite
em memória e um pipeline falso. Garante que o `POST /api/v1/jobs` agenda o
processamento (202) e que o background task transiciona o status do job.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from src.core.errors import GenerationError
from src.core.worker import JobProcessor
from src.models.video_job import JobStatus, VideoJob


class OkPipeline:
    """Pipeline falso que grava um MP4 e conclui."""

    def __init__(self, tmp_path) -> None:
        self._tmp = tmp_path
        self.jobs: list[str] = []

    def run(self, job: VideoJob):
        self.jobs.append(job.id)
        out = self._tmp / f"{job.id}.mp4"
        out.write_bytes(b"mp4")
        return out


class BoomPipeline:
    """Pipeline falso que sempre falha."""

    def __init__(self) -> None:
        self.jobs: list[str] = []

    def run(self, job: VideoJob):
        self.jobs.append(job.id)
        raise GenerationError("falhou no pipeline")


@pytest.fixture()
def engine():
    e = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(e)
    return e


def _build_client(engine, pipeline) -> TestClient:
    from src.api import deps
    from src.api.main import create_app

    def override_session():
        with Session(engine) as s:
            yield s

    app = create_app()
    app.dependency_overrides[deps.get_session] = override_session
    app.dependency_overrides[deps.get_job_processor] = lambda: JobProcessor(
        pipeline, engine, timeout=5
    )
    return TestClient(app, raise_server_exceptions=True)


class TestJobDispatchIntegration:
    def test_post_returns_202_and_runs_background_to_completed(
        self, engine, tmp_path
    ) -> None:
        pipeline = OkPipeline(tmp_path)
        with _build_client(engine, pipeline) as client:
            r = client.post("/api/v1/jobs", json={"prompt": "um gato astronauta"})
            assert r.status_code == 202
            job_id = r.json()["id"]

            # A resposta é serializada como pending antes do background rodar.
            assert r.json()["status"] == "pending"

            # O background task (executado pelo TestClient) completou o job.
            with Session(engine) as s:
                job = s.get(VideoJob, job_id)
                assert job.status == JobStatus.COMPLETED
                assert job.output_path is not None

        assert pipeline.jobs == [job_id]

    def test_get_reflects_background_completion(self, engine, tmp_path) -> None:
        pipeline = OkPipeline(tmp_path)
        with _build_client(engine, pipeline) as client:
            job_id = client.post("/api/v1/jobs", json={"prompt": "x"}).json()["id"]

            r = client.get(f"/api/v1/jobs/{job_id}")

            assert r.status_code == 200
            assert r.json()["status"] == "completed"
            assert r.json()["output_url"] is not None

    def test_failing_pipeline_marks_job_failed(self, engine) -> None:
        pipeline = BoomPipeline()
        with _build_client(engine, pipeline) as client:
            r = client.post("/api/v1/jobs", json={"prompt": "x"})
            assert r.status_code == 202
            job_id = r.json()["id"]

            with Session(engine) as s:
                job = s.get(VideoJob, job_id)
                assert job.status == JobStatus.FAILED
                assert job.error_message == "falhou no pipeline"

        assert pipeline.jobs == [job_id]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
