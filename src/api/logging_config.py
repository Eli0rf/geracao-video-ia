"""
src/api/logging_config.py — Configuração de logging estruturado com structlog.

Produz logs em JSON em produção e em formato legível em desenvolvimento.
"""

import logging
import sys

import structlog

from src.config import get_settings


class _CorrelationIdFilter(logging.Filter):
    """
    Injeta o `correlation_id` ativo (structlog contextvars) em todo LogRecord
    nativo do Python, para que logs de terceiros (uvicorn, SQLAlchemy) também
    carreguem o ID de rastreabilidade (E07).
    """

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            value = structlog.contextvars.get_contextvars().get("correlation_id")
        except Exception:  # pragma: no cover - contextvars sempre disponível
            value = None
        record.correlation_id = str(value) if value else "-"
        return True


def configure_logging() -> None:
    """
    Configura structlog + logging padrão do Python.

    Em development: saída colorida e legível no terminal.
    Em production/test: JSON estruturado para ingestão por ferramentas de log.
    """
    settings = get_settings()
    is_dev = settings.is_development
    log_level = settings.log_level

    # Configura o logging padrão do Python (captura logs de bibliotecas terceiras)
    fmt = "%(message)s" if is_dev else "%(correlation_id)s %(message)s"
    logging.basicConfig(
        format=fmt,
        stream=sys.stdout,
        level=getattr(logging, log_level, logging.INFO),
    )
    for handler in logging.getLogger().handlers:
        handler.addFilter(_CorrelationIdFilter())

    # Processors comuns a todos os ambientes
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if is_dev:
        # Desenvolvimento: saída legível com cores
        processors: list[structlog.types.Processor] = [
            *shared_processors,
            structlog.dev.ConsoleRenderer(),
        ]
    else:
        # Produção/teste: JSON estruturado
        processors = [
            *shared_processors,
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Retorna um logger estruturado com o nome do módulo."""
    result: structlog.stdlib.BoundLogger = structlog.get_logger(name)
    return result
