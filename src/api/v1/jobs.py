"""
src/api/v1/jobs.py — Endpoints de geração de vídeo.

POST   /api/v1/jobs              → cria job (202)
GET    /api/v1/jobs              → lista jobs com paginação
GET    /api/v1/jobs/{id}         → status do job
GET    /api/v1/jobs/{id}/download → download do vídeo gerado
"""

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, field_validator
from sqlmodel import Session

from src.api.deps import get_job_processor, get_session
from src.api.error_handlers import _problem_response
from src.core.dispatcher import BackgroundTasksDispatcher
from src.core.worker import JobProcessor
from src.models.video_job import JobStatus, VideoJob
from src.models.video_job_crud import (
    create_video_job,
    get_video_job,
    list_video_jobs,
)

router = APIRouter(prefix="/jobs", tags=["jobs"])

# Modelos permitidos — qualquer valor fora deste conjunto é rejeitado
_ALLOWED_MODELS = {"animatediff", "cogvideox", "wan2.1", "hunyuan", "fake"}


# ── Schemas de request/response ───────────────────────────────────────────────

class JobCreateRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=2000)
    model: str = Field(default="animatediff")
    duration_seconds: int = Field(default=5, ge=1, le=60)
    width: int = Field(default=848, ge=64, le=1920)
    height: int = Field(default=480, ge=64, le=1080)

    @field_validator("model")
    @classmethod
    def validate_model(cls, v: str) -> str:
        if v not in _ALLOWED_MODELS:
            msg = f"modelo '{v}' inválido. Use: {sorted(_ALLOWED_MODELS)}"
            raise ValueError(msg)
        return v

    @field_validator("width")
    @classmethod
    def validate_width_multiple_of_8(cls, v: int) -> int:
        if v % 8 != 0:
            raise ValueError("width deve ser múltiplo de 8")
        return v

    @field_validator("height")
    @classmethod
    def validate_height_multiple_of_8(cls, v: int) -> int:
        if v % 8 != 0:
            raise ValueError("height deve ser múltiplo de 8")
        return v


class JobResponse(BaseModel):
    id: str
    status: JobStatus
    prompt: str
    model: str
    duration_seconds: int
    width: int
    height: int
    output_url: str | None
    error_message: str | None
    created_at: str
    updated_at: str

    @classmethod
    def from_job(cls, job: VideoJob) -> "JobResponse":
        output_url = (
            f"/api/v1/jobs/{job.id}/download"
            if job.status == JobStatus.COMPLETED
            else None
        )
        return cls(
            id=job.id,
            status=job.status,
            prompt=job.prompt,
            model=job.model,
            duration_seconds=job.duration_seconds,
            width=job.width,
            height=job.height,
            output_url=output_url,
            error_message=job.error_message,
            created_at=job.created_at.isoformat(),
            updated_at=job.updated_at.isoformat(),
        )


class JobListResponse(BaseModel):
    items: list[JobResponse]
    total: int
    page: int
    page_size: int


# ── Endpoints ─────────────────────────────────────────────────────────────────

SessionDep = Annotated[Session, Depends(get_session)]
ProcessorDep = Annotated[JobProcessor, Depends(get_job_processor)]


@router.post("", status_code=202, response_model=JobResponse)
async def post_job(
    body: JobCreateRequest,
    session: SessionDep,
    background_tasks: BackgroundTasks,
    processor: ProcessorDep,
) -> JobResponse:
    """Cria um novo job (pending) e agenda o processamento em background (202)."""
    job = create_video_job(
        session,
        prompt=body.prompt,
        model=body.model,
        duration_seconds=body.duration_seconds,
        width=body.width,
        height=body.height,
    )
    BackgroundTasksDispatcher(background_tasks, processor).dispatch(job.id)
    return JobResponse.from_job(job)


@router.get("", response_model=JobListResponse)
async def list_jobs(
    session: SessionDep,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: JobStatus | None = Query(default=None),
) -> JobListResponse:
    """Lista jobs com paginação e filtro opcional por status."""
    jobs, total = list_video_jobs(session, page=page, page_size=page_size, status=status)
    return JobListResponse(
        items=[JobResponse.from_job(j) for j in jobs],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: str, session: SessionDep) -> JobResponse:
    """Retorna o status de um job pelo ID."""
    job = get_video_job(session, job_id)
    if job is None:
        return _problem_response(404, f"Job '{job_id}' não encontrado.")  # type: ignore[return-value]
    return JobResponse.from_job(job)


@router.get("/{job_id}/download")
async def download_job(job_id: str, session: SessionDep) -> FileResponse:
    """Baixa o vídeo gerado de um job concluído."""
    job = get_video_job(session, job_id)

    if job is None:
        return _problem_response(404, f"Job '{job_id}' não encontrado.")  # type: ignore[return-value]

    if job.status != JobStatus.COMPLETED:
        return _problem_response(  # type: ignore[return-value]
            409,
            f"Job está em status '{job.status.value}' — disponível apenas quando 'completed'.",
        )

    if job.output_path is None or not Path(job.output_path).exists():
        return _problem_response(410, "Arquivo de vídeo não encontrado no servidor.")  # type: ignore[return-value]

    return FileResponse(
        path=job.output_path,
        media_type="video/mp4",
        filename=f"video_{job_id}.mp4",
    )
