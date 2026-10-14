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
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import structlog.contextvars
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.staticfiles import StaticFiles

from src.api.deps import get_engine
from src.api.error_handlers import http_exception_handler, validation_exception_handler
from src.api.logging_config import configure_logging, get_logger
from src.api.schemas import HealthResponse
from src.api.v1.metrics import router as metrics_router
from src.api.v1.router import router as v1_router
from src.config import get_settings
from src.core.worker import recover_stale_jobs

# Inicializa logging antes de qualquer outro import que possa logar
configure_logging()

logger = get_logger(__name__)
settings = get_settings()

# Diretório do frontend (raiz do projeto) — caminho absoluto p/ independência do CWD
STATIC_DIR = Path(__file__).resolve().parents[2] / "static"


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Na subida, recupera jobs presos em `processing` (exceto em testes)."""
    if not settings.is_testing:
        try:
            recovered = recover_stale_jobs(get_engine())
            logger.info("startup_stale_recovery", recovered=recovered)
        except Exception as exc:  # nunca impede a aplicação de subir
            logger.warning("startup_stale_recovery_failed", error=str(exc))
    yield


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
        lifespan=lifespan,
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
    # /metrics na raiz (convenção Prometheus) — o mesmo router também é
    # montado em /api/v1/metrics via v1_router.
    application.include_router(metrics_router)
    application.include_router(v1_router)

    # ── Middleware de logging + correlation id de rastreabilidade (E07) ───────
    @application.middleware("http")
    async def log_requests(request: Request, call_next):  # type: ignore[no-untyped-def]
        # Usa o X-Correlation-ID do cliente ou gera um novo (uuid hex).
        correlation_id = request.headers.get("X-Correlation-ID") or uuid.uuid4().hex
        request.state.correlation_id = correlation_id
        structlog.contextvars.bind_contextvars(correlation_id=correlation_id)
        start = time.perf_counter()
        try:
            response = await call_next(request)
        finally:
            structlog.contextvars.unbind_contextvars("correlation_id")
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.info(
            "request",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
            correlation_id=correlation_id,
        )
        response.headers["X-Correlation-ID"] = correlation_id
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

    # ── Frontend estático (Bloco 5 / TASK-021) ─────────────────────────────────
    # Mount por último: o catch-all "/" não pode sombrear /api/v1/* nem /health.
    if STATIC_DIR.is_dir():
        application.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
    else:  # pragma: no cover - falha de empacotamento, nunca em dev/CI
        logger.warning("static_dir_missing", path=str(STATIC_DIR))

    logger.info(
        "app_created",
        version=settings.app_version,
        environment=settings.app_env,
    )

    return application


# Instância usada pelo uvicorn: `uvicorn src.api.main:app`
app = create_app()
