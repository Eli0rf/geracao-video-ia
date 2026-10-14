"""
src/api/v1/metrics.py — Endpoint GET /metrics (TASK-014 / E07).

Saída em texto puro no formato Prometheus, contada diretamente no banco
(SQLite), sem bibliotecas externas:

    # HELP video_jobs_total Total de jobs por status.
    # TYPE video_jobs_total counter
    video_jobs_total{status="pending"} 2
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy import func
from sqlmodel import Session, select

from src.api.deps import get_session
from src.models.video_job import VideoJob

router = APIRouter(prefix="/metrics", tags=["metrics"])

_HELP = "# HELP video_jobs_total Total de jobs por status."
_TYPE = "# TYPE video_jobs_total counter"

SessionDep = Annotated[Session, Depends(get_session)]


@router.get("", response_class=PlainTextResponse)
def get_metrics(session: SessionDep) -> str:
    """Contagem rápida de jobs agrupada por status, em texto Prometheus."""
    rows = session.exec(
        select(VideoJob.status, func.count()).group_by(VideoJob.status)
    ).all()
    lines = [_HELP, _TYPE]
    for status, count in sorted(rows, key=lambda r: str(r[0])):
        status_value = getattr(status, "value", status)
        lines.append(f'video_jobs_total{{status="{status_value}"}} {count}')
    return "\n".join(lines) + "\n"
