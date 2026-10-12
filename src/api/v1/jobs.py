"""
src/api/v1/jobs.py — Endpoints de geração de vídeo.

Rotas implementadas aqui:
  POST /api/v1/jobs        → cria novo job (TASK-005)
  GET  /api/v1/jobs        → lista jobs    (TASK-007)
  GET  /api/v1/jobs/{id}   → status job    (TASK-006)
  GET  /api/v1/jobs/{id}/download → download (TASK-008)

Este arquivo contém apenas o placeholder POST /api/v1/jobs para que a
estrutura de routers esteja presente desde a TASK-002.
Os endpoints completos são implementados na TASK-005~008.
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(prefix="/jobs", tags=["jobs"])


class JobCreateRequest(BaseModel):
    """Schema de request para criação de job — placeholder até TASK-005."""

    prompt: str = Field(min_length=1, max_length=2000, description="Prompt de geração")
    model: str = Field(default="animatediff", description="Modelo de IA a usar")


@router.post("", status_code=202)
async def create_job(body: JobCreateRequest) -> dict[str, str]:
    """
    Cria um novo job de geração de vídeo (placeholder).

    Implementação completa na TASK-005.
    """
    # Placeholder — retorna accepted imediatamente sem persistir
    return {"status": "pending", "message": "job recebido — implementação completa na TASK-005"}
