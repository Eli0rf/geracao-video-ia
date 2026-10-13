"""
src/api/deps.py — Dependências FastAPI (Dependency Injection).

get_session() é a dependência central injetada em todos os endpoints
que precisam de acesso ao banco de dados.
"""

from collections.abc import Generator

from sqlalchemy import Engine
from sqlmodel import Session, create_engine

from src.config import get_settings
from src.core.assembly.ffmpeg import VideoAssembler
from src.core.factory import (
    get_audio_synthesizer,
    get_generator,
    get_script_generator,
)
from src.core.pipeline import VideoPipeline
from src.core.worker import JobProcessor

_settings = get_settings()
_engine = create_engine(
    _settings.database_url,
    connect_args={"check_same_thread": False},  # necessário para SQLite
)


def get_engine() -> Engine:
    """Retorna o engine compartilhado da aplicação (usado também pelo worker)."""
    return _engine


def get_session() -> Generator[Session]:
    """
    Fornece uma sessão de banco de dados para cada request.

    Usada via Depends(get_session) nos endpoints.
    Pode ser sobrescrita em testes via app.dependency_overrides.
    """
    with Session(_engine) as session:
        yield session


def get_job_processor() -> JobProcessor:
    """
    Constrói o `JobProcessor` com o pipeline real (factory + VideoAssembler).

    Os geradores são resolvidos via factory (com fallback para fakes quando o
    serviço real está indisponível). Injetável/sobrescrevível nos testes via
    `app.dependency_overrides`.
    """
    settings = get_settings()
    pipeline = VideoPipeline(
        script_generator=get_script_generator(),
        audio_synthesizer=get_audio_synthesizer(),
        video_generator=get_generator(settings.default_model),
        assembler=VideoAssembler(),
        output_dir=settings.output_dir,
    )
    return JobProcessor(pipeline=pipeline, engine=_engine)
