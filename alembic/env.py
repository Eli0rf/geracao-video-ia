"""
alembic/env.py — Configuração do Alembic para SQLModel.

Carrega o DATABASE_URL de src/config.py e usa os metadados do SQLModel
para gerar migrations automáticas com --autogenerate.
"""

import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# Garante que src/ está no path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Importa os modelos para que o SQLModel.metadata os conheça
from src.models.video_job import VideoJob  # noqa: F401 — necessário para autogenerate
from src.config import get_settings
from sqlmodel import SQLModel

# Objeto de configuração do Alembic
config = context.config

# Carrega logging do alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata com todos os modelos registrados
target_metadata = SQLModel.metadata


def get_url() -> str:
    """Retorna a URL do banco a partir das configurações da aplicação."""
    settings = get_settings()
    return settings.database_url


def run_migrations_offline() -> None:
    """
    Modo offline: gera SQL sem conectar ao banco.

    Útil para gerar scripts de migração para revisão.
    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,  # necessário para SQLite (ALTER TABLE limitado)
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Modo online: conecta ao banco e aplica migrations.

    Usado em produção via `alembic upgrade head`.
    """
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,  # necessário para SQLite
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
