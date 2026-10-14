"""
Testes de rastreabilidade (E07) — correlation id do middleware ao worker:

  - middleware ecoa/gera `X-Correlation-ID` e o encaminha ao processor;
  - dispatcher repassa `correlation_id` mantendo compat com assinatura antiga;
  - `JobProcessor` binda `correlation_id` + `job_id` nos contextvars do
    structlog, inclusive dentro da thread do pipeline.
"""

from unittest.mock import MagicMock

import pytest
import structlog.contextvars
from fastapi import BackgroundTasks
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from src.core.dispatcher import BackgroundTasksDispatcher
from src.core.worker import JobProcessor


@pytest.fixture()
def engine():
    """Engine SQLite em memória com StaticPool."""
    e = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(e)
    return e


@pytest.fixture()
def client(engine):
    from src.api import deps
    from src.api.main import create_app

    class _Recorder:
        def __init__(self) -> None:
            self.calls: list[tuple[str, str | None]] = []

        async def process(self, job_id: str, correlation_id: str | None = None) -> None:
            self.calls.append((job_id, correlation_id))

    recorder = _Recorder()

    def override():
        with Session(engine) as s:
            yield s

    app = create_app()
    app.dependency_overrides[deps.get_session] = override
    app.dependency_overrides[deps.get_job_processor] = lambda: recorder
    with TestClient(app) as c:
        c.recorder = recorder  # type: ignore[attr-defined]
        yield c


class TestCorrelationMiddleware:
    def test_echoes_provided_header(self, client) -> None:
        r = client.post(
            "/api/v1/jobs",
            json={"prompt": "t"},
            headers={"X-Correlation-ID": "corr-123"},
        )
        assert r.status_code == 202
        assert r.headers["X-Correlation-ID"] == "corr-123"

    def test_generates_id_when_header_absent(self, client) -> None:
        r = client.post("/api/v1/jobs", json={"prompt": "t"})
        cid = r.headers.get("X-Correlation-ID")
        assert cid, "middleware deve gerar X-Correlation-ID"
        assert len(cid) >= 16

    def test_forwards_provided_id_to_processor(self, client) -> None:
        r = client.post(
            "/api/v1/jobs",
            json={"prompt": "t"},
            headers={"X-Correlation-ID": "corr-xyz"},
        )
        job_id = r.json()["id"]
        assert client.recorder.calls == [(job_id, "corr-xyz")]  # type: ignore[attr-defined]

    def test_forwards_generated_id_to_processor(self, client) -> None:
        r = client.post("/api/v1/jobs", json={"prompt": "t"})
        job_id = r.json()["id"]
        cid = r.headers["X-Correlation-ID"]
        assert client.recorder.calls == [(job_id, cid)]  # type: ignore[attr-defined]


class TestDispatcherCorrelation:
    def test_without_correlation_keeps_single_positional_arg(self) -> None:
        class StrictSpy:
            """Assinatura antiga (só job_id) — compat obrigatória."""

            async def process(self, job_id: str) -> None:  # pragma: no cover
                raise AssertionError("não deve ser executado")

        tasks = BackgroundTasks()
        BackgroundTasksDispatcher(tasks, StrictSpy()).dispatch("job-1")
        task = tasks.tasks[0]
        assert task.args == ("job-1",)
        assert task.kwargs == {}

    def test_with_correlation_passes_as_kwarg(self) -> None:
        class Spy:
            async def process(self, job_id: str, correlation_id: str | None = None) -> None:
                pass  # pragma: no cover

        tasks = BackgroundTasks()
        BackgroundTasksDispatcher(tasks, Spy()).dispatch("job-1", correlation_id="c1")
        task = tasks.tasks[0]
        assert task.args == ("job-1",)
        assert task.kwargs == {"correlation_id": "c1"}


class _CtxRecorder:
    """Logger falso que registra (evento, contextvars) no momento da chamada."""

    def __init__(self) -> None:
        self.records: list[tuple[str, dict]] = []

    def info(self, event: str, **kwargs: object) -> None:
        self.records.append((event, dict(structlog.contextvars.get_contextvars())))

    def warning(self, event: str, **kwargs: object) -> None:
        self.records.append((event, dict(structlog.contextvars.get_contextvars())))


class TestWorkerCorrelationBinding:
    @pytest.mark.asyncio
    async def test_binds_correlation_and_job_id_including_thread(
        self, engine, monkeypatch
    ) -> None:
        from src.core import worker as worker_mod

        recorder = _CtxRecorder()
        monkeypatch.setattr(worker_mod, "logger", recorder)
        processor = JobProcessor(MagicMock(), engine, timeout=5)

        # Job inexistente: `_process_sync` roda na thread e loga job_not_found.
        await processor.process("nao-existe", correlation_id="corr-42")

        not_found = next(e for e in recorder.records if e[0] == "job_not_found")
        assert not_found[1].get("correlation_id") == "corr-42"
        assert not_found[1].get("job_id") == "nao-existe"

        processed = next(e for e in recorder.records if e[0] == "job_processed")
        assert processed[1].get("correlation_id") == "corr-42"
        assert processed[1].get("job_id") == "nao-existe"

    @pytest.mark.asyncio
    async def test_without_correlation_still_binds_job_id(self, engine, monkeypatch) -> None:
        from src.core import worker as worker_mod

        recorder = _CtxRecorder()
        monkeypatch.setattr(worker_mod, "logger", recorder)
        processor = JobProcessor(MagicMock(), engine, timeout=5)

        await processor.process("outro-nao-existe")

        processed = next(e for e in recorder.records if e[0] == "job_processed")
        assert processed[1].get("job_id") == "outro-nao-existe"
        assert "correlation_id" not in processed[1]
