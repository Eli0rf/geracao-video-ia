"""
src/core/dispatcher.py — Despacho de jobs para execução em background (TASK-020).

Define a abstração `JobDispatcher` (Protocol) e a implementação concreta
baseada em `FastAPI.BackgroundTasks`. O endpoint `POST /jobs` depende apenas
do Protocol, o que permite trocar por um `CeleryDispatcher` no futuro sem
alterar o endpoint nem o `JobProcessor`. Vide ADR-008.
"""

from typing import Protocol, runtime_checkable

from fastapi import BackgroundTasks

from src.core.worker import JobProcessor


@runtime_checkable
class JobDispatcher(Protocol):
    """Abstração de despacho: enfileira um `job_id` para processamento."""

    def dispatch(self, job_id: str) -> None:
        """Agenda o processamento do job `job_id` em background."""
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

    def dispatch(self, job_id: str) -> None:
        """Agenda `processor.process(job_id)` para rodar após a resposta."""
        self._tasks.add_task(self._processor.process, job_id)
