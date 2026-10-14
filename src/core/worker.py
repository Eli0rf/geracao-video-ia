"""
src/core/worker.py — Processamento em background dos VideoJobs (TASK-020).

`JobProcessor` consome um job `pending`, executa o `VideoPipeline` e faz as
transições de status no banco:

    pending → processing → completed (com output_path)
                           ↘ failed   (com error_message)

Roda em background (via `BackgroundTasksDispatcher`), por isso **abre sua
própria sessão** SQLAlchemy — não reutiliza a sessão de request. O trabalho
bloqueante (pipeline) é executado em thread (`asyncio.to_thread`) e limitado
por um semáforo (`max_concurrent_jobs`) e por timeout (`job_timeout_seconds`).
Vide ADR-008.
"""

import asyncio
import time
from typing import Any

import structlog
import structlog.contextvars
from sqlalchemy import Engine
from sqlmodel import Session, select

from src.config import get_settings
from src.core.errors import GenerationError
from src.core.pipeline import VideoPipeline
from src.models.video_job import JobStatus, VideoJob
from src.models.video_job_crud import update_job_status

logger = structlog.get_logger(__name__)

# Limita o tamanho da mensagem de erro persistida no banco.
_MAX_ERROR_CHARS = 2000


class JobProcessor:
    """
    Processa VideoJobs em background gerenciando suas transições de status.

    Args:
        pipeline: Orquestrador da geração (`VideoPipeline`).
        engine: Engine SQLAlchemy — cada job abre sua própria `Session`.
        timeout: Tempo máximo por job, em segundos (default das settings).
        max_concurrent: Jobs simultâneos (default das settings).
    """

    def __init__(
        self,
        pipeline: VideoPipeline,
        engine: Engine,
        timeout: float | None = None,
        max_concurrent: int | None = None,
    ) -> None:
        settings = get_settings()
        self._pipeline = pipeline
        self._engine = engine
        self._timeout = timeout if timeout is not None else settings.job_timeout_seconds
        self._max_concurrent = (
            max_concurrent if max_concurrent is not None else settings.max_concurrent_jobs
        )
        self._semaphore = asyncio.Semaphore(self._max_concurrent)

    async def process(self, job_id: str, correlation_id: str | None = None) -> None:
        """
        Processa um job de ponta a ponta (thread + timeout + semáforo).

        Idempotente: jobs que não estão mais `pending` são ignorados.

        Vincula `job_id` (+ `correlation_id` quando fornecido) aos contextvars
        do structlog: os logs do pipeline dentro da thread (`asyncio.to_thread`
        copia o contexto) herdam o rastreamento de ponta a ponta (E07).
        """
        start = time.perf_counter()
        bound: dict[str, Any] = {"job_id": job_id}
        if correlation_id is not None:
            bound["correlation_id"] = correlation_id
        with structlog.contextvars.bound_contextvars(**bound):
            async with self._semaphore:
                try:
                    await asyncio.wait_for(
                        asyncio.to_thread(self._process_sync, job_id),
                        timeout=self._timeout,
                    )
                except TimeoutError as exc:
                    self._mark_failed(
                        job_id, f"Timeout após {self._timeout}s de processamento."
                    )
                    logger.warning("job_timeout", job_id=job_id, error=str(exc))
                except GenerationError as exc:
                    # _process_sync já trata a maior parte; esta é uma rede de segurança.
                    self._mark_failed(job_id, str(exc))
                    logger.warning("job_generation_error", job_id=job_id, error=str(exc))
                finally:
                    duration_ms = round((time.perf_counter() - start) * 1000, 2)
                    logger.info("job_processed", job_id=job_id, duration_ms=duration_ms)

    def _process_sync(self, job_id: str) -> None:
        """Executa o pipeline em thread, abrindo a própria sessão do banco."""
        with Session(self._engine) as session:
            job = session.get(VideoJob, job_id)
            if job is None:
                logger.warning("job_not_found", job_id=job_id)
                return
            if job.status != JobStatus.PENDING:
                # Idempotência: não reprocessa jobs já em andamento/concluídos.
                logger.info("job_skipped_not_pending", job_id=job_id, status=job.status.value)
                return

            update_job_status(session, job_id, JobStatus.PROCESSING)

            try:
                out_path = self._pipeline.run(job)
            except Exception as exc:  # captura ampla: qualquer falha vira `failed`
                message = str(exc)[:_MAX_ERROR_CHARS] or exc.__class__.__name__
                update_job_status(session, job_id, JobStatus.FAILED, error_message=message)
                logger.warning("job_failed", job_id=job_id, error=message)
                return

            update_job_status(
                session, job_id, JobStatus.COMPLETED, output_path=str(out_path)
            )
            logger.info("job_completed", job_id=job_id, out=str(out_path))

    def _mark_failed(self, job_id: str, message: str) -> None:
        """Marca o job como `failed` usando uma sessão própria (usado no timeout)."""
        with Session(self._engine) as session:
            update_job_status(session, job_id, JobStatus.FAILED, error_message=message)


def recover_stale_jobs(engine: Engine, stale_after_minutes: int = 30) -> int:
    """
    Marca como `failed` jobs presos em `processing` (ex.: processo derrubado).

    Considera "preso" todo job `processing` cujo `updated_at` é mais antigo
    que `stale_after_minutes`. Chamado no `lifespan` da aplicação (ADR-008).

    Args:
        engine: Engine SQLAlchemy.
        stale_after_minutes: Idade mínima de `updated_at` para considerar preso.

    Returns:
        Quantidade de jobs recuperados.
    """
    from datetime import UTC, datetime, timedelta

    from sqlmodel import SQLModel

    # Garante que a tabela exista (idempotente) — seguro rodar na subida.
    SQLModel.metadata.create_all(engine)
    cutoff = datetime.now(UTC) - timedelta(minutes=stale_after_minutes)

    with Session(engine) as session:
        stmt = select(VideoJob).where(
            VideoJob.status == JobStatus.PROCESSING,
            VideoJob.updated_at < cutoff,
        )
        stale = list(session.exec(stmt).all())
        for job in stale:
            update_job_status(
                session,
                job.id,
                JobStatus.FAILED,
                error_message="Job interrompido (recuperado na inicialização).",
            )
        logger.info("stale_jobs_recovered", count=len(stale))
        return len(stale)

