"""
Testes para `src/core/job_service.py` (E12).

O worker Celery precisa montar o `JobProcessor` sem importar `src.api.deps`
(acoplamento API → core). Estas funções extraem essa construção e ficam
compartilhadas entre a API e o worker.
"""

from unittest.mock import MagicMock

import pytest
from sqlmodel import create_engine

from src.core.job_service import build_job_processor
from src.core.worker import JobProcessor


@pytest.fixture()
def engine():
    """Engine SQLite em memória — suficiente para inspecionar o processor."""
    return create_engine("sqlite://", connect_args={"check_same_thread": False})


class TestBuildJobProcessor:
    def test_returns_job_processor(self, engine) -> None:
        assert isinstance(build_job_processor(engine), JobProcessor)

    def test_uses_the_given_engine(self, engine) -> None:
        assert build_job_processor(engine)._engine is engine

    def test_builds_a_real_pipeline(self, engine) -> None:
        from src.core.pipeline import VideoPipeline

        processor = build_job_processor(engine)
        assert isinstance(processor._pipeline, VideoPipeline)

    def test_timeout_comes_from_settings_by_default(self, engine) -> None:
        from src.config import get_settings

        settings = get_settings()
        assert build_job_processor(engine)._timeout == settings.job_timeout_seconds

    def test_accepts_explicit_timeout(self, engine) -> None:
        assert build_job_processor(engine, timeout=42)._timeout == 42

    def test_accepts_explicit_pipeline(self, engine) -> None:
        pipeline = MagicMock()
        assert build_job_processor(engine, pipeline=pipeline)._pipeline is pipeline


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
