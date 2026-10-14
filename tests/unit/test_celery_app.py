"""
Testes para a aplicação Celery e a task de processamento (E12).

Cobre `src/core/celery_app.py` sem exigir um Redis ativo: o app é criado com
`task_always_eager` (execução síncrona em memória) e o `JobProcessor` é
substituído por um espião, de modo que a task exercite apenas o contrato
(nome registrado, argumentos repassados, binding de correlation_id nos
contextvars do structlog).
"""

import pytest
import structlog.contextvars

from src.core import celery_app as celery_mod
from src.core.celery_app import process_job


class _CtxRecorder:
    """Logger falso que registra (evento, contextvars) no momento da chamada."""

    def __init__(self) -> None:
        self.records: list[tuple[str, dict]] = []

    def info(self, event: str, **kwargs: object) -> None:
        self.records.append((event, dict(structlog.contextvars.get_contextvars())))

    def warning(self, event: str, **kwargs: object) -> None:
        self.records.append((event, dict(structlog.contextvars.get_contextvars())))

    def error(self, event: str, **kwargs: object) -> None:
        self.records.append((event, dict(structlog.contextvars.get_contextvars())))


class SpyProcessor:
    """Processor falso: registra as chamadas sem tocar no pipeline."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str | None]] = []

    async def process(self, job_id: str, correlation_id: str | None = None) -> None:
        self.calls.append((job_id, correlation_id))


@pytest.fixture()
def spy_processor(monkeypatch: pytest.MonkeyPatch) -> SpyProcessor:
    """Substitui o processor construído pela task por um espião."""
    spy = SpyProcessor()
    monkeypatch.setattr(celery_mod, "_build_processor", lambda: spy)
    return spy


class TestCeleryAppConfig:
    def test_app_has_expected_name(self) -> None:
        assert celery_mod.celery.main == "geracao_video"

    def test_broker_comes_from_settings(self) -> None:
        settings = celery_mod.get_settings()
        assert celery_mod.celery.conf.broker_url == settings.celery_broker_url

    def test_result_backend_comes_from_settings(self) -> None:
        settings = celery_mod.get_settings()
        assert celery_mod.celery.conf.result_backend == settings.celery_result_backend

    def test_task_is_registered_under_expected_name(self) -> None:
        assert process_job.name == "video.process_job"


class TestProcessJobTask:
    def test_task_calls_processor_with_job_id(self, spy_processor: SpyProcessor) -> None:
        process_job.delay("job-abc")

        assert spy_processor.calls == [("job-abc", None)]

    def test_task_forwards_correlation_id(self, spy_processor: SpyProcessor) -> None:
        process_job.delay("job-abc", correlation_id="corr-9")

        assert spy_processor.calls == [("job-abc", "corr-9")]

    def test_task_binds_correlation_id_in_contextvars(
        self, spy_processor: SpyProcessor, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        recorder = _CtxRecorder()
        monkeypatch.setattr(celery_mod, "logger", recorder)

        process_job.delay("job-ctx", correlation_id="corr-ctx")

        started = next(e for e in recorder.records if e[0] == "job_task_received")
        assert started[1].get("correlation_id") == "corr-ctx"
        assert started[1].get("job_id") == "job-ctx"

        finished = next(e for e in recorder.records if e[0] == "job_task_finished")
        assert finished[1].get("correlation_id") == "corr-ctx"

    def test_task_binds_job_id_without_correlation(
        self, spy_processor: SpyProcessor, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        recorder = _CtxRecorder()
        monkeypatch.setattr(celery_mod, "logger", recorder)

        process_job.delay("job-solo")

        finished = next(e for e in recorder.records if e[0] == "job_task_finished")
        assert finished[1].get("job_id") == "job-solo"
        assert "correlation_id" not in finished[1]

    def test_task_propagates_processor_exception(self) -> None:
        class Boom:
            async def process(self, job_id: str, correlation_id: str | None = None) -> None:
                raise RuntimeError("pipeline explodiu")

        celery_mod._build_processor = Boom  # type: ignore[assignment]
        try:
            with pytest.raises(RuntimeError, match="pipeline explodiu"):
                process_job.delay("job-boom")
        finally:
            del celery_mod._build_processor


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
