"""
Testes da seleção de backend de execução (E12).

O endpoint `POST /api/v1/jobs` não escolhe diretamente a classe concreta:
pede o dispatcher a `resolve_dispatcher()`, que decide entre `CeleryDispatcher`
(produção) e `BackgroundTasksDispatcher` (dev/teste). Assim os testes de API
seguem verdes sem Redis e o CI não precisa de broker.
"""

from unittest.mock import MagicMock

import pytest
from fastapi import BackgroundTasks

from src.config import get_settings
from src.core.dispatcher import BackgroundTasksDispatcher, CeleryDispatcher, JobDispatcher
from src.core.job_service import resolve_dispatcher


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> None:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _env(monkeypatch: pytest.MonkeyPatch, **values: str) -> None:
    for key, value in values.items():
        monkeypatch.setenv(key, value)
    get_settings.cache_clear()


class TestTaskBackendSetting:
    def test_defaults_to_background(self) -> None:
        assert get_settings().task_backend == "background"

    def test_accepts_celery(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _env(monkeypatch, TASK_BACKEND="celery")
        assert get_settings().task_backend == "celery"

    def test_accepts_uppercase_and_trims(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _env(monkeypatch, TASK_BACKEND=" CELERY ")
        assert get_settings().task_backend == "celery"

    def test_rejects_unknown_value(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from src.config import Settings

        with pytest.raises(ValueError, match="task_backend"):
            Settings(_env_file=None, task_backend="kafka")

    def test_celery_urls_have_defaults(self) -> None:
        settings = get_settings()
        assert settings.celery_broker_url.startswith("redis://")
        assert settings.celery_result_backend.startswith("redis://")


class TestResolveDispatcher:
    def test_returns_background_dispatcher_in_development(self) -> None:
        dispatcher = resolve_dispatcher(BackgroundTasks(), MagicMock())
        assert isinstance(dispatcher, BackgroundTasksDispatcher)

    def test_returns_background_dispatcher_in_test(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _env(monkeypatch, APP_ENV="test")
        dispatcher = resolve_dispatcher(BackgroundTasks(), MagicMock())
        assert isinstance(dispatcher, BackgroundTasksDispatcher)

    def test_returns_celery_dispatcher_in_production(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _env(monkeypatch, APP_ENV="production", TASK_BACKEND="celery")
        assert isinstance(resolve_dispatcher(BackgroundTasks()), CeleryDispatcher)

    def test_honours_explicit_celery_backend(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _env(monkeypatch, APP_ENV="development", TASK_BACKEND="celery")
        assert isinstance(resolve_dispatcher(BackgroundTasks()), CeleryDispatcher)

    def test_result_satisfies_protocol(self, monkeypatch: pytest.MonkeyPatch) -> None:
        assert isinstance(resolve_dispatcher(BackgroundTasks(), MagicMock()), JobDispatcher)

    def test_background_dispatcher_receives_processor(self) -> None:
        processor = MagicMock()
        dispatcher = resolve_dispatcher(BackgroundTasks(), processor)
        assert dispatcher._processor is processor

    def test_background_requires_a_processor(self) -> None:
        with pytest.raises(AssertionError, match="JobProcessor"):
            resolve_dispatcher(BackgroundTasks())


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
