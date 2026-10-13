"""
Testes para JobDispatcher / BackgroundTasksDispatcher (src/core/dispatcher.py).

Valida que o despacho agenda `processor.process(job_id)` via `BackgroundTasks`
do FastAPI e que a implementação satisfaz o Protocol `JobDispatcher`.
"""

import pytest
from fastapi import BackgroundTasks

from src.core.dispatcher import BackgroundTasksDispatcher, JobDispatcher


class SpyProcessor:
    """Processor falso que registra os job_ids processados."""

    def __init__(self) -> None:
        self.processed: list[str] = []

    async def process(self, job_id: str) -> None:
        self.processed.append(job_id)


class TestBackgroundTasksDispatcher:
    def test_dispatch_adds_one_task(self) -> None:
        tasks = BackgroundTasks()
        processor = SpyProcessor()

        BackgroundTasksDispatcher(tasks, processor).dispatch("job-1")

        assert len(tasks.tasks) == 1

    def test_dispatch_registers_processor_process(self) -> None:
        tasks = BackgroundTasks()
        processor = SpyProcessor()

        BackgroundTasksDispatcher(tasks, processor).dispatch("job-1")

        task = tasks.tasks[0]
        assert task.func == processor.process
        assert task.args == ("job-1",)

    def test_dispatch_multiple_jobs(self) -> None:
        tasks = BackgroundTasks()
        processor = SpyProcessor()
        dispatcher = BackgroundTasksDispatcher(tasks, processor)

        dispatcher.dispatch("job-1")
        dispatcher.dispatch("job-2")

        assert len(tasks.tasks) == 2

    async def test_scheduled_task_calls_processor(self) -> None:
        tasks = BackgroundTasks()
        processor = SpyProcessor()
        BackgroundTasksDispatcher(tasks, processor).dispatch("job-xyz")

        await tasks()  # executa as tarefas agendadas

        assert processor.processed == ["job-xyz"]


class TestJobDispatcherProtocol:
    def test_background_dispatcher_satisfies_protocol(self) -> None:
        tasks = BackgroundTasks()
        processor = SpyProcessor()
        dispatcher = BackgroundTasksDispatcher(tasks, processor)

        assert isinstance(dispatcher, JobDispatcher)

    def test_object_without_dispatch_does_not_satisfy(self) -> None:
        class NotDispatcher:
            pass

        assert not isinstance(NotDispatcher(), JobDispatcher)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
