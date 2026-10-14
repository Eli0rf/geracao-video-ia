"""
src/core/celery_app.py — Aplicação Celery + task de processamento (E12).

Ponto de entrada do worker:

    celery -A src.core.celery_app worker --loglevel=info

A task `process_job` apenas traduz a mensagem da fila em uma chamada ao
`JobProcessor` — toda a lógica de geração (pipeline, status, timeout)
continua em `src/core/worker.py`, exatamente como previa o ADR-008. O que
muda é **onde** o trabalho roda: num processo dedicado, fora do servidor web.

Configuração:
  - broker/backend: Redis (`settings.celery_broker_url` / `celery_result_backend`);
  - `acks_late=True`: a mensagem só é confirmada **depois** do job terminar,
    então um worker morto no meio não perde o job (ele volta para a fila);
  - `task_always_eager`: em testes, a task roda em memória, sem broker.
"""

import asyncio
from typing import Any

import structlog
import structlog.contextvars
from celery import Celery
from celery.signals import worker_process_init

from src.config import get_settings
from src.core.job_service import build_job_processor, configure_worker
from src.core.worker import JobProcessor

logger = structlog.get_logger(__name__)

settings = get_settings()

# Em teste a task roda em memória (sem broker): a suíte nunca precisa de Redis.
# Em produção, `celery_task_always_eager` continua false e a fila é real.
_always_eager = settings.celery_task_always_eager or settings.is_testing

celery = Celery(
    "geracao_video",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["src.core.celery_app"],
)

celery.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_always_eager=_always_eager,
    # Propaga exceções em modo eager (testes) em vez de engolir no resultado.
    task_eager_propagates=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_track_started=True,
    # Limite rígido = timeout de job já parametrizado nas settings.
    task_time_limit=settings.job_timeout_seconds,
    task_soft_time_limit=max(1, settings.job_timeout_seconds - 30),
    worker_max_tasks_per_child=50,
    timezone="UTC",
    enable_utc=True,
)


# `worker_process_init.connect` é um decorador sem anotações (mypy: untyped).
@worker_process_init.connect  # type: ignore[misc]
def _configure_worker_logging(**_kwargs: Any) -> None:
    """Configura o logging estruturado dentro do processo do worker (E07)."""
    configure_worker()


def _build_processor() -> JobProcessor:
    """Monta o processor do worker (ponto único de injeção para os testes)."""
    from src.core.database import get_engine

    return build_job_processor(get_engine())


# `celery.task` devolve um objeto sem anotações de tipo (mypy: decorator untyped).
@celery.task(name="video.process_job", bind=True, acks_late=True)  # type: ignore[misc]
def process_job(
    self: Any,
    job_id: str,
    correlation_id: str | None = None,
) -> None:
    """
    Processa um `VideoJob` de ponta a ponta dentro do worker Celery.

    Args:
        job_id: Identificador do job a processar.
        correlation_id: ID de rastreabilidade da request original (E07),
            repassado pelo `CeleryDispatcher`.

    Raises:
        Exception: Qualquer falha do pipeline é propagada para que o Celery
            registre a task como falha (com `acks_late`, a mensagem volta à
            fila caso o worker tenha morrido).
    """
    bound: dict[str, Any] = {"job_id": job_id}
    if correlation_id is not None:
        bound["correlation_id"] = correlation_id

    with structlog.contextvars.bound_contextvars(**bound):
        logger.info("job_task_received", task_id=str(self.request.id))
        try:
            processor = _build_processor()
            asyncio.run(processor.process(job_id, correlation_id=correlation_id))
        except Exception:
            logger.exception("job_task_failed")
            raise
        logger.info("job_task_finished")
