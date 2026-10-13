"""
Testes para JobProcessor e recover_stale_jobs (src/core/worker.py).

Usam um engine SQLite em arquivo (tmp_path) para exercitar as transições
reais de status com segurança de concorrência (cada `Session` recebe a sua
conexão — importante no teste de timeout, onde uma thread e o loop principal
escrevem ao mesmo tempo). Um pipeline falso substitui o `VideoPipeline` real
— sem I/O de IA/FFmpeg.
"""

import tempfile
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlmodel import Session, SQLModel, create_engine

from src.core.errors import GenerationError
from src.core.worker import JobProcessor, recover_stale_jobs
from src.models.video_job import JobStatus, VideoJob
from src.models.video_job_crud import create_video_job


class FakePipeline:
    """Pipeline falso: grava um arquivo de saída e devolve o caminho."""

    def __init__(self, delay: float = 0.0, raises: Exception | None = None) -> None:
        self.calls: list[str] = []
        self._delay = delay
        self._raises = raises

    def run(self, job: VideoJob) -> Path:
        self.calls.append(job.id)
        if self._delay:
            time.sleep(self._delay)
        if self._raises is not None:
            raise self._raises
        out = Path(tempfile.gettempdir()) / f"fake_out_{job.id}.mp4"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(b"mp4")
        return out


@pytest.fixture()
def engine(tmp_path: Path):
    """Engine SQLite em arquivo temporário — conexões independentes e seguras."""
    e = create_engine(
        f"sqlite:///{tmp_path}/worker.db",
        connect_args={"check_same_thread": False},
    )
    SQLModel.metadata.create_all(e)
    yield e
    e.dispose()


def _get_status(engine, job_id: str) -> JobStatus:
    with Session(engine) as s:
        job = s.get(VideoJob, job_id)
        assert job is not None
        return job.status


class TestJobProcessorSuccess:
    @pytest.mark.asyncio
    async def test_pending_to_completed(self, engine) -> None:
        with Session(engine) as s:
            job = create_video_job(s, prompt="gato")
        pipeline = FakePipeline()
        processor = JobProcessor(pipeline, engine, timeout=5)

        await processor.process(job.id)

        assert _get_status(engine, job.id) == JobStatus.COMPLETED
        with Session(engine) as s:
            assert s.get(VideoJob, job.id).output_path is not None
        assert pipeline.calls == [job.id]

    @pytest.mark.asyncio
    async def test_opens_own_session(self, engine) -> None:
        # O processor não recebe sessão de request — usa o engine diretamente.
        with Session(engine) as s:
            job = create_video_job(s, prompt="gato")
        processor = JobProcessor(FakePipeline(), engine, timeout=5)

        await processor.process(job.id)

        assert _get_status(engine, job.id) == JobStatus.COMPLETED


class TestJobProcessorFailure:
    @pytest.mark.asyncio
    async def test_generation_error_marks_failed(self, engine) -> None:
        with Session(engine) as s:
            job = create_video_job(s, prompt="gato")
        pipeline = FakePipeline(raises=GenerationError("sem VRAM"))
        processor = JobProcessor(pipeline, engine, timeout=5)

        await processor.process(job.id)

        assert _get_status(engine, job.id) == JobStatus.FAILED
        with Session(engine) as s:
            assert s.get(VideoJob, job.id).error_message == "sem VRAM"

    @pytest.mark.asyncio
    async def test_unexpected_error_marks_failed(self, engine) -> None:
        with Session(engine) as s:
            job = create_video_job(s, prompt="gato")
        pipeline = FakePipeline(raises=RuntimeError("bug inesperado"))
        processor = JobProcessor(pipeline, engine, timeout=5)

        await processor.process(job.id)

        assert _get_status(engine, job.id) == JobStatus.FAILED
        with Session(engine) as s:
            assert s.get(VideoJob, job.id).error_message == "bug inesperado"

    @pytest.mark.asyncio
    async def test_timeout_marks_failed(self, engine) -> None:
        with Session(engine) as s:
            job = create_video_job(s, prompt="gato")
        # Bloqueia além do timeout; a thread final levanta erro, mas o estado
        # final é FAILED em ambos os caminhos (determinístico para o assert).
        pipeline = FakePipeline(delay=0.3, raises=GenerationError("tarde demais"))
        processor = JobProcessor(pipeline, engine, timeout=0.05)

        await processor.process(job.id)

        assert _get_status(engine, job.id) == JobStatus.FAILED
        with Session(engine) as s:
            assert s.get(VideoJob, job.id).error_message is not None


class TestJobProcessorIdempotency:
    @pytest.mark.asyncio
    async def test_skips_non_pending_job(self, engine) -> None:
        from src.models.video_job_crud import update_job_status

        with Session(engine) as s:
            job = create_video_job(s, prompt="gato")
            update_job_status(s, job.id, JobStatus.COMPLETED)
        pipeline = FakePipeline()
        processor = JobProcessor(pipeline, engine, timeout=5)

        await processor.process(job.id)

        # Não reprocessa: pipeline nunca roda, status permanece completed.
        assert pipeline.calls == []
        assert _get_status(engine, job.id) == JobStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_unknown_job_is_ignored(self, engine) -> None:
        pipeline = FakePipeline()
        processor = JobProcessor(pipeline, engine, timeout=5)

        await processor.process("00000000-0000-0000-0000-000000000000")

        assert pipeline.calls == []


class TestRecoverStaleJobs:
    def _set_job(self, engine, status: JobStatus, updated_at: datetime) -> str:
        from src.models.video_job_crud import update_job_status

        with Session(engine) as s:
            job = create_video_job(s, prompt="preso")
            job_id = job.id
            update_job_status(s, job_id, status)
            job.updated_at = updated_at
            s.add(job)
            s.commit()
        return job_id

    def test_marks_old_processing_as_failed(self, engine) -> None:
        old = datetime.now(UTC) - timedelta(hours=1)
        job_id = self._set_job(engine, JobStatus.PROCESSING, old)

        recovered = recover_stale_jobs(engine, stale_after_minutes=30)

        assert recovered == 1
        assert _get_status(engine, job_id) == JobStatus.FAILED

    def test_keeps_recent_processing(self, engine) -> None:
        recent = datetime.now(UTC) - timedelta(minutes=1)
        job_id = self._set_job(engine, JobStatus.PROCESSING, recent)

        recovered = recover_stale_jobs(engine, stale_after_minutes=30)

        assert recovered == 0
        assert _get_status(engine, job_id) == JobStatus.PROCESSING

    def test_ignores_non_processing_jobs(self, engine) -> None:
        old = datetime.now(UTC) - timedelta(hours=1)
        pending_id = self._set_job(engine, JobStatus.PENDING, old)

        recovered = recover_stale_jobs(engine, stale_after_minutes=30)

        assert recovered == 0
        assert _get_status(engine, pending_id) == JobStatus.PENDING

    def test_returns_zero_when_empty(self, engine) -> None:
        assert recover_stale_jobs(engine) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

