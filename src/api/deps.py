"""
src/api/deps.py — Dependências FastAPI (Dependency Injection).

get_session() é a dependência central injetada em todos os endpoints
que precisam de acesso ao banco de dados.
"""

from collections.abc import Generator

from sqlmodel import Session

from src.core.database import get_engine
from src.core.job_service import build_job_processor
from src.core.worker import JobProcessor


def get_session() -> Generator[Session]:
    """
    Fornece uma sessão de banco de dados para cada request.

    Usada via Depends(get_session) nos endpoints.
    Pode ser sobrescrita em testes via app.dependency_overrides.
    """
    with Session(get_engine()) as session:
        yield session


def get_job_processor() -> JobProcessor:
    """
    Constrói o `JobProcessor` com o pipeline real (factory + VideoAssembler).

    A montagem vive em `src.core.job_service` para ser compartilhada com o
    worker Celery (E12); esta dependência apenas a expõe para injeção no
    endpoint — sobrescrevível nos testes via `app.dependency_overrides`.
    """
    return build_job_processor(get_engine())


__all__ = ["get_engine", "get_job_processor", "get_session"]

