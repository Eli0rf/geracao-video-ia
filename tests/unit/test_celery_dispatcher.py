"""
Testes para o `CeleryDispatcher` (src/core/dispatcher.py) — E12.

O dispatcher é a peça que liga o endpoint `POST /jobs` à fila Celery. Os
testes mockam a task (`process_job.delay`) para garantir que a suíte roda sem
Redis, verificando os argumentos repassados e a compatibilidade com o
Protocol `JobDispatcher`.
"""

from unittest.mock import MagicMock

import pytest

from src.core.dispatcher import BackgroundTasksDispatcher, CeleryDispatcher, JobDispatcher


@pytest.fixture()
def mock_task() -> MagicMock:
    """Task Celery falsa que apenas registra as chamadas de `.delay`."""
    return MagicMock()


class TestCeleryDispatcher:
    def test_delay_called_with_job_id(self, mock_task: MagicMock) -> None:
        CeleryDispatcher(mock_task).dispatch("job-1")

        mock_task.delay.assert_called_once_with("job-1")

    def test_delay_called_with_correlation_id(self, mock_task: MagicMock) -> None:
        CeleryDispatcher(mock_task).dispatch("job-1", correlation_id="corr-1")

        mock_task.delay.assert_called_once_with("job-1", correlation_id="corr-1")

    def test_dispatch_returns_none(self, mock_task: MagicMock) -> None:
        assert CeleryDispatcher(mock_task).dispatch("job-1") is None

    def test_multiple_jobs_are_enqueued(self, mock_task: MagicMock) -> None:
        dispatcher = CeleryDispatcher(mock_task)
        dispatcher.dispatch("job-1")
        dispatcher.dispatch("job-2")

        assert mock_task.delay.call_count == 2

    def test_satisfies_job_dispatcher_protocol(self, mock_task: MagicMock) -> None:
        assert isinstance(CeleryDispatcher(mock_task), JobDispatcher)

    def test_defaults_to_process_job_task(self) -> None:
        from src.core.celery_app import process_job

        assert CeleryDispatcher()._task is process_job


class TestBackgroundDispatcherStillAvailable:
    """O dispatcher antigo permanece como caminho de dev/teste (ADR-008)."""

    def test_still_satisfies_protocol(self) -> None:
        from fastapi import BackgroundTasks

        assert isinstance(BackgroundTasksDispatcher(BackgroundTasks(), MagicMock()), JobDispatcher)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
