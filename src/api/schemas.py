"""
src/api/schemas.py — Schemas Pydantic compartilhados entre routers.

Inclui o formato de erro RFC 7807 (Problem Details for HTTP APIs).
"""

from pydantic import BaseModel, Field


class ProblemDetail(BaseModel):
    """
    Formato de erro padronizado RFC 7807 — Problem Details for HTTP APIs.

    Referência: https://datatracker.ietf.org/doc/html/rfc7807
    """

    type: str = Field(
        default="about:blank",
        description="URI que identifica o tipo do problema",
    )
    title: str = Field(
        description="Descrição curta e legível do tipo do problema",
    )
    status: int = Field(
        description="Código de status HTTP",
    )
    detail: str = Field(
        description="Explicação específica desta ocorrência do problema",
    )
    instance: str | None = Field(
        default=None,
        description="URI que identifica a ocorrência específica do problema",
    )

    model_config = {"json_schema_extra": {"example": {
        "type": "about:blank",
        "title": "Not Found",
        "status": 404,
        "detail": "O recurso solicitado não foi encontrado.",
    }}}


class HealthResponse(BaseModel):
    """Resposta do endpoint GET /health."""

    status: str = Field(default="ok", description="Status da aplicação")
    version: str = Field(description="Versão da aplicação")
    environment: str = Field(description="Ambiente de execução (development/production/test)")
