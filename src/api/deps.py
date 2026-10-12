"""
src/api/deps.py — Dependências FastAPI (Dependency Injection).

get_session() é a dependência central injetada em todos os endpoints
que precisam de acesso ao banco de dados.
"""

from collections.abc import Generator

from sqlmodel import Session, create_engine

from src.config import get_settings

_settings = get_settings()
_engine = create_engine(
    _settings.database_url,
    connect_args={"check_same_thread": False},  # necessário para SQLite
)


def get_session() -> Generator[Session]:
    """
    Fornece uma sessão de banco de dados para cada request.

    Usada via Depends(get_session) nos endpoints.
    Pode ser sobrescrita em testes via app.dependency_overrides.
    """
    with Session(_engine) as session:
        yield session
