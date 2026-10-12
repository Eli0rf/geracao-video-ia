"""
Testes de integração para CRUD de VideoJob (src/models/video_job.py).

Usa SQLite em memória. Testa create, get, list, update_status.
"""

import pytest
from sqlmodel import Session, SQLModel, create_engine

from src.models.video_job import JobStatus, VideoJob
from src.models.video_job_crud import (
    create_video_job,
    get_video_job,
    list_video_jobs,
    update_job_status,
)


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:", echo=False)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


class TestCreateVideoJob:
    def test_create_returns_job_with_id(self, session: Session) -> None:
        job = create_video_job(session, prompt="a red dragon flying")
        assert job.id is not None
        assert job.prompt == "a red dragon flying"
        assert job.status == JobStatus.PENDING

    def test_create_with_custom_model(self, session: Session) -> None:
        job = create_video_job(session, prompt="test", model="cogvideox")
        assert job.model == "cogvideox"

    def test_create_with_custom_dimensions(self, session: Session) -> None:
        job = create_video_job(session, prompt="test", width=1280, height=720)
        assert job.width == 1280
        assert job.height == 720


class TestGetVideoJob:
    def test_get_existing_job(self, session: Session) -> None:
        created = create_video_job(session, prompt="find me")
        found = get_video_job(session, created.id)
        assert found is not None
        assert found.id == created.id
        assert found.prompt == "find me"

    def test_get_nonexistent_returns_none(self, session: Session) -> None:
        result = get_video_job(session, "00000000-0000-0000-0000-000000000000")
        assert result is None


class TestListVideoJobs:
    def test_list_empty_returns_empty(self, session: Session) -> None:
        jobs, total = list_video_jobs(session)
        assert jobs == []
        assert total == 0

    def test_list_returns_all_jobs(self, session: Session) -> None:
        create_video_job(session, prompt="job1")
        create_video_job(session, prompt="job2")
        create_video_job(session, prompt="job3")
        jobs, total = list_video_jobs(session)
        assert total == 3
        assert len(jobs) == 3

    def test_list_pagination(self, session: Session) -> None:
        for i in range(5):
            create_video_job(session, prompt=f"job{i}")
        jobs, total = list_video_jobs(session, page=1, page_size=2)
        assert total == 5
        assert len(jobs) == 2

    def test_list_page_two(self, session: Session) -> None:
        for i in range(5):
            create_video_job(session, prompt=f"job{i}")
        jobs, total = list_video_jobs(session, page=2, page_size=2)
        assert total == 5
        assert len(jobs) == 2

    def test_list_filter_by_status(self, session: Session) -> None:
        j1 = create_video_job(session, prompt="pending job")
        j2 = create_video_job(session, prompt="completed job")
        update_job_status(session, j2.id, JobStatus.COMPLETED)

        pending, total = list_video_jobs(session, status=JobStatus.PENDING)
        assert total == 1
        assert pending[0].id == j1.id

    def test_list_ordered_newest_first(self, session: Session) -> None:
        j1 = create_video_job(session, prompt="first")
        j2 = create_video_job(session, prompt="second")
        jobs, _ = list_video_jobs(session)
        # Mais recente primeiro
        assert jobs[0].id == j2.id
        assert jobs[1].id == j1.id


class TestUpdateJobStatus:
    def test_update_to_processing(self, session: Session) -> None:
        job = create_video_job(session, prompt="test")
        updated = update_job_status(session, job.id, JobStatus.PROCESSING)
        assert updated is not None
        assert updated.status == JobStatus.PROCESSING

    def test_update_to_completed_with_path(self, session: Session) -> None:
        job = create_video_job(session, prompt="test")
        updated = update_job_status(
            session, job.id, JobStatus.COMPLETED,
            output_path="/outputs/videos/abc.mp4"
        )
        assert updated is not None
        assert updated.status == JobStatus.COMPLETED
        assert updated.output_path == "/outputs/videos/abc.mp4"

    def test_update_to_failed_with_message(self, session: Session) -> None:
        job = create_video_job(session, prompt="test")
        updated = update_job_status(
            session, job.id, JobStatus.FAILED,
            error_message="CUDA out of memory"
        )
        assert updated is not None
        assert updated.status == JobStatus.FAILED
        assert updated.error_message == "CUDA out of memory"

    def test_update_nonexistent_returns_none(self, session: Session) -> None:
        result = update_job_status(
            session, "00000000-0000-0000-0000-000000000000", JobStatus.PROCESSING
        )
        assert result is None
