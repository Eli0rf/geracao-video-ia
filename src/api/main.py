"""
src/api/main.py — Entry point da aplicação FastAPI.

Cria e configura a instância da aplicação:
  - Logging estruturado
  - Error handlers RFC 7807
  - Routers v1
  - Middleware de logging de requests
  - Endpoint /health
"""

import time

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.api.error_handlers import http_exception_handler, validation_exception_handler
from src.api.logging_config import configure_logging, get_logger
from src.api.schemas import HealthResponse
from src.api.v1.router import router as v1_router
from src.config import get_settings

# Inicializa logging antes de qualquer outro import que possa logar
configure_logging()

logger = get_logger(__name__)
settings = get_settings()


def create_app() -> FastAPI:
    """
    Factory da aplicação FastAPI.

    Separado do módulo-nível para facilitar testes e hot-reload.
    """
    application = FastAPI(
        title="Geração de Vídeo por IA",
        description="API REST para geração de vídeos com modelos open-source.",
        version=settings.app_version,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # ── Error handlers RFC 7807 ───────────────────────────────────────────────
    application.add_exception_handler(
        StarletteHTTPException,
        http_exception_handler,  # type: ignore[arg-type]
    )
    application.add_exception_handler(
        RequestValidationError,
        validation_exception_handler,  # type: ignore[arg-type]
    )

    # ── Routers ───────────────────────────────────────────────────────────────
    application.include_router(v1_router)

    # ── Middleware de logging de requests ─────────────────────────────────────
    @application.middleware("http")
    async def log_requests(request: Request, call_next):  # type: ignore[no-untyped-def]
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.info(
            "request",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )
        return response

    # ── Healthcheck ───────────────────────────────────────────────────────────
    @application.get(
        "/health",
        response_model=HealthResponse,
        tags=["system"],
        summary="Healthcheck da aplicação",
    )
    async def health() -> HealthResponse:
        """Retorna o status da aplicação, versão e ambiente."""
        return HealthResponse(
            status="ok",
            version=settings.app_version,
            environment=settings.app_env,
        )

    logger.info(
        "app_created",
        version=settings.app_version,
        environment=settings.app_env,
    )

    return application


# Instância usada pelo uvicorn: `uvicorn src.api.main:app`
app = create_app()
