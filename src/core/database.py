"""
src/core/database.py — Engine SQLAlchemy compartilhado (E12).

Antes o engine vivia em `src/api/deps.py`, o que obrigaria o worker Celery
(módulo de `core`) a importar a camada de API. Aqui ele vive no core e é
compartilhado pelo processo web e pelo worker, mantendo **um único engine por
processo**.
"""

from functools import lru_cache

from sqlalchemy import Engine, create_engine

from src.config import get_settings


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """
    Retorna o engine compartilhado da aplicação.

    Usa `lru_cache` para criar o engine apenas uma vez por processo (a API e o
    worker têm ciclos de vida longos; o engine é thread-safe e deve ser
    reutilizado).

    O parâmetro `check_same_thread=False` é necessário para o SQLite aceitar
    conexões vindas de threads diferentes (o `JobProcessor` processa em thread).
    """
    settings = get_settings()
    return create_engine(settings.database_url, connect_args={"check_same_thread": False})
