"""
conftest.py — Configuração global do pytest.

Garante que `src/` está no sys.path para todos os testes.
Define fixtures compartilhadas entre unit, integration e e2e.
"""

import sys
from pathlib import Path

import pytest

# Garante que a raiz do projeto está no path Python
# Necessário para `import src.config` funcionar independente de como pytest é invocado
sys.path.insert(0, str(Path(__file__).parent))


@pytest.fixture(autouse=True)
def _celery_always_eager() -> None:
    """
    Força a task Celery a rodar em memória durante toda a suíte (E12).

    Sem isso, `.delay()` tentaria conectar ao Redis e travaria os testes.
    Aplica-se a todos os módulos de teste (autouse) porque a app Celery é um
    singleton criado no import — basta ajustar a conf antes do uso.
    """
    from src.core import celery_app as celery_mod

    celery_mod.celery.conf.task_always_eager = True
    yield
    celery_mod.celery.conf.task_always_eager = False

