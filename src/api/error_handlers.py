"""
src/api/error_handlers.py — Handlers de erro padronizados RFC 7807.

Converte exceções FastAPI/Starlette para o formato Problem Details.
"""

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.api.schemas import ProblemDetail

# Mapa de status code → título HTTP padrão
_HTTP_STATUS_TITLES: dict[int, str] = {
    400: "Bad Request",
    401: "Unauthorized",
    403: "Forbidden",
    404: "Not Found",
    405: "Method Not Allowed",
    409: "Conflict",
    410: "Gone",
    422: "Unprocessable Entity",
    429: "Too Many Requests",
    500: "Internal Server Error",
    503: "Service Unavailable",
}


def _problem_response(
    status_code: int,
    detail: str,
    title: str | None = None,
    problem_type: str = "about:blank",
) -> JSONResponse:
    """Monta um JSONResponse no formato RFC 7807."""
    resolved_title = title or _HTTP_STATUS_TITLES.get(status_code, "Error")
    body = ProblemDetail(
        type=problem_type,
        title=resolved_title,
        status=status_code,
        detail=detail,
    )
    return JSONResponse(
        status_code=status_code,
        content=body.model_dump(exclude_none=True),
        media_type="application/problem+json",
    )


async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    """Converte HTTPException para RFC 7807."""
    detail = str(exc.detail) if exc.detail else _HTTP_STATUS_TITLES.get(exc.status_code, "Error")
    return _problem_response(exc.status_code, detail)


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Converte erros de validação Pydantic (422) para RFC 7807."""
    # Constrói um detail legível a partir dos erros de validação
    errors = exc.errors()
    detail_parts: list[str] = []
    for err in errors:
        loc = " → ".join(str(p) for p in err.get("loc", []))
        msg = err.get("msg", "valor inválido")
        detail_parts.append(f"{loc}: {msg}")
    detail = "; ".join(detail_parts) if detail_parts else "Dados de entrada inválidos."
    return _problem_response(422, detail)
