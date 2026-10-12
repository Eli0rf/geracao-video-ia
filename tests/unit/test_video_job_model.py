"""
Testes unitários para o modelo VideoJob (src/models/video_job.py).

Verifica criação, validação de campos, defaults e transições de status.
Sem I/O real — usa SQLite em memória via fixture.
"""

from datetime import datetime, timezone

import pytest
from sqlmodel import Session, SQLModel, create_engine

from src.models.video_job import JobStatus, VideoJob


@pytest.fixture()
def session():
    """Sessão SQLite em memória — isolada por teste."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


class TestVideoJobModel:
    def test_create_minimal(self, session: Session) -> None:
        """Cria VideoJob com apenas o prompt obrigatório."""
        job = VideoJob(prompt="a cat on the moon")
        session.add(job)
        session.commit()
        session.refresh(job)

        assert job.id is not None
        assert job.prompt == "a cat on the moon"

    def test_default_status_is_pending(self, session: Session) -> None:
        job = VideoJob(prompt="test")
        session.add(job)
        session.commit()
        session.refresh(job)
        assert job.status == JobStatus.PENDING

    def test_default_model_is_animatediff(self, session: Session) -> None:
        job = VideoJob(prompt="test")
        session.add(job)
        session.commit()
        session.refresh(job)
        assert job.model == "animatediff"

    def test_default_duration(self, session: Session) -> None:
        job = VideoJob(prompt="test")
        session.add(job)
        session.commit()
        session.refresh(job)
        assert job.duration_seconds == 5

    def test_default_dimensions(self, session: Session) -> None:
        job = VideoJob(prompt="test")
        session.add(job)
        session.commit()
        session.refresh(job)
        assert job.width == 848
        assert job.height == 480

    def test_output_path_starts_none(self, session: Session) -> None:
        job = VideoJob(prompt="test")
        session.add(job)
        session.commit()
        session.refresh(job)
        assert job.output_path is None

    def test_error_message_starts_none(self, session: Session) -> None:
        job = VideoJob(prompt="test")
        session.add(job)
        session.commit()
        session.refresh(job)
        assert job.error_message is None

    def test_created_at_is_set(self, session: Session) -> None:
        job = VideoJob(prompt="test")
        session.add(job)
        session.commit()
        session.refresh(job)
        assert isinstance(job.created_at, datetime)

    def test_custom_model(self, session: Session) -> None:
        job = VideoJob(prompt="test", model="wan2.1")
        session.add(job)
        session.commit()
        session.refresh(job)
        assert job.model == "wan2.1"

    def test_custom_dimensions(self, session: Session) -> None:
        job = VideoJob(prompt="test", width=1280, height=720)
        session.add(job)
        session.commit()
        session.refresh(job)
        assert job.width == 1280
        assert job.height == 720


class TestJobStatus:
    def test_all_statuses_exist(self) -> None:
        assert JobStatus.PENDING == "pending"
        assert JobStatus.PROCESSING == "processing"
        assert JobStatus.COMPLETED == "completed"
        assert JobStatus.FAILED == "failed"

    def test_status_is_string(self) -> None:
        """JobStatus values são strings (para serialização JSON direta)."""
        for status in JobStatus:
            assert isinstance(status.value, str)
