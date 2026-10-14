"""
src/core/dispatcher.py — Despacho de jobs para execução em background (TASK-020).

Define a abstração `JobDispatcher` (Protocol) e duas implementações concretas:

- `BackgroundTasksDispatcher` — executa no mesmo processo do FastAPI, sem
  broker. Usada em desenvolvimento/teste.
- `CeleryDispatcher` — enfileira na fila Redis processada por um worker
  dedicado. Usada em produção (E12 / ADR-009).

O endpoint `POST /jobs` depende apenas do Protocol (via
`src.core.job_service.resolve_dispatcher`), portanto nenhuma das duas
implementações é acoplada ao endpoint nem ao `JobProcessor`. Vide ADR-008
e ADR-009.
"""

from typing import Protocol, runtime_checkable

from fastapi import BackgroundTasks

from src.core.worker import JobProcessor


@runtime_checkable
class JobDispatcher(Protocol):
    """Abstração de despacho: enfileira um `job_id` para processamento."""

    def dispatch(self, job_id: str, correlation_id: str | None = None) -> None:
        """
        Agenda o processamento do job `job_id` em background.

        Args:
            job_id: Identificador do job.
            correlation_id: ID de rastreabilidade repassado ao processor
                (opcional — quando ausente, a assinatura antiga é mantida).
        """
        ...


class BackgroundTasksDispatcher:
    """
    `JobDispatcher` baseado em `BackgroundTasks` do FastAPI.

    Args:
        tasks: `BackgroundTasks` injetado na request.
        processor: `JobProcessor` que executará o job.
    """

    def __init__(self, tasks: BackgroundTasks, processor: JobProcessor) -> None:
        self._tasks = tasks
        self._processor = processor

    def dispatch(self, job_id: str, correlation_id: str | None = None) -> None:
        """
        Agenda `processor.process(job_id)` para rodar após a resposta.

        Quando `correlation_id` é fornecido, é repassado como kwarg — sem
        ele, a chamada permanece `process(job_id)` (compat com implementações
        que não conhecem o parâmetro, E07).
        """
        if correlation_id is None:
            self._tasks.add_task(self._processor.process, job_id)
        else:
            self._tasks.add_task(
                self._processor.process, job_id, correlation_id=correlation_id
            )


class CeleryDispatcher:
    """
    `JobDispatcher` baseado em fila Celery (broker Redis) — E12 / ADR-009.

    O processamento pesado sai do processo web e roda em um worker dedicado
    (`celery -A src.core.celery_app worker`), o que garante que uma queda da
    API não perca jobs em execução (a mensagem permanece na fila).

    Args:
        task: Task Celery de processamento. Quando ausente, usa
            `src.core.celery_app.process_job` (import tardio para não acoplar
            este módulo ao Celery em ambientes que não o utilizam).
    """

    def __init__(self, task: object | None = None) -> None:
        self._task = task if task is not None else self._default_task()

    @staticmethod
    def _default_task() -> object:
        """Resolve a task padrão sob demanda (evita import no topo do módulo)."""
        from src.core.celery_app import process_job

        return process_job

    def dispatch(self, job_id: str, correlation_id: str | None = None) -> None:
        """
        Enfileira o processamento do job no broker.

        Quando `correlation_id` é fornecido, é repassado como kwarg para que o
        worker herde o rastreamento de ponta a ponta (E07); sem ele, a chamada
        permanece `delay(job_id)`.
        """
        if correlation_id is None:
            self._task.delay(job_id)  # type: ignore[attr-defined]
        else:
            self._task.delay(job_id, correlation_id=correlation_id)  # type: ignore[attr-defined]
