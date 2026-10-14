"""
src/core/job_service.py — Montagem do `JobProcessor` compartilhada (E12).

O endpoint `POST /jobs` e o worker Celery precisam do **mesmo** `JobProcessor`
(pipeline real + engine). Antes essa construção vivia em `src/api/deps.py`,
o que forçaria o worker a importar a camada de API. Aqui ela vive no core e
`deps.get_job_processor()` passa a delegar para cá (fim da duplicação).

Também concentra a escolha do despachante (`resolve_dispatcher`), isolando o
endpoint da decisão entre `BackgroundTasksDispatcher` (dev/teste) e
`CeleryDispatcher` (produção). Vide ADR-009.
"""

import structlog
from fastapi import BackgroundTasks
from sqlalchemy import Engine

from src.api.logging_config import configure_logging
from src.config import get_settings
from src.core.assembly.ffmpeg import VideoAssembler
from src.core.dispatcher import (
    BackgroundTasksDispatcher,
    CeleryDispatcher,
    JobDispatcher,
)
from src.core.factory import (
    get_audio_synthesizer,
    get_generator,
    get_script_generator,
)
from src.core.pipeline import VideoPipeline
from src.core.worker import JobProcessor

logger = structlog.get_logger(__name__)


def build_job_processor(
    engine: Engine,
    pipeline: VideoPipeline | None = None,
    timeout: float | None = None,
) -> JobProcessor:
    """
    Monta um `JobProcessor` com o pipeline real de geração.

    Args:
        engine: Engine SQLAlchemy usado pelo processor (cada job abre sessão).
        pipeline: Pipeline já construído (injeção para testes). Quando ausente,
            é montado com os geradores resolvidos pela factory + `VideoAssembler`.
        timeout: Timeout por job em segundos (default das settings).

    Returns:
        `JobProcessor` pronto para processar jobs.
    """
    if pipeline is None:
        settings = get_settings()
        pipeline = VideoPipeline(
            script_generator=get_script_generator(),
            audio_synthesizer=get_audio_synthesizer(),
            video_generator=get_generator(settings.default_model),
            assembler=VideoAssembler(),
            output_dir=settings.output_dir,
        )
    return JobProcessor(pipeline=pipeline, engine=engine, timeout=timeout)


def resolve_dispatcher(
    tasks: BackgroundTasks,
    processor: JobProcessor | None = None,
) -> JobDispatcher:
    """
    Retorna o despachante adequado ao ambiente.

    - `task_backend="background"` (padrão: dev/teste) → `BackgroundTasksDispatcher`,
      que executa no mesmo processo e **não precisa de broker**.
    - `task_backend="celery"` → `CeleryDispatcher`, que enfileira na fila Redis.

    Args:
        tasks: `BackgroundTasks` da request (ignorado pelo dispatcher Celery).
        processor: `JobProcessor` usado pelo dispatcher de background. Quando
            ausente, o dispatcher Celery não precisa dele.

    Returns:
        Implementação concreta de `JobDispatcher`.
    """
    settings = get_settings()
    if settings.task_backend == "celery":
        return CeleryDispatcher()
    assert processor is not None, "BackgroundTasksDispatcher exige um JobProcessor"
    return BackgroundTasksDispatcher(tasks, processor)


def configure_worker() -> None:
    """
    Prepara o processo do worker Celery (chamado no topo de `celery_app`).

    O worker não passa pelo `src.api.main`, então o logging estruturado e o
    filtro de `correlation_id` (E07) precisam ser configurados aqui para que
    os logs emitidos pelas tasks fiquem no mesmo formato da API.
    """
    configure_logging()
    logger.info("celery_worker_configured", environment=get_settings().app_env)


__all__ = [
    "build_job_processor",
    "configure_worker",
    "resolve_dispatcher",
]
