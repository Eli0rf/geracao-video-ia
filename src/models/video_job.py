"""
src/models/video_job.py — Entidade VideoJob com SQLModel.

Define o modelo de dados para jobs de geração de vídeo.
Compatível com SQLite (dev) e PostgreSQL (produção futura).
"""

import uuid
from datetime import UTC, datetime
from enum import Enum

from sqlmodel import Field, SQLModel


class JobStatus(str, Enum):
    """Status possíveis de um job de geração de vídeo."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


def _utcnow() -> datetime:
    """Retorna o timestamp UTC atual (helper para default_factory)."""
    return datetime.now(UTC)


def _new_uuid() -> str:
    """Gera um UUID v4 como string."""
    return str(uuid.uuid4())


class VideoJob(SQLModel, table=True):
    """
    Job de geração de vídeo.

    Representa uma solicitação de geração desde a criação (pending)
    até a conclusão (completed) ou falha (failed).
    """

    __tablename__ = "video_jobs"

    # ── Identidade ─────────────────────────────────────────────────────────
    id: str = Field(
        default_factory=_new_uuid,
        primary_key=True,
        description="UUID v4 único do job",
    )

    # ── Entrada ────────────────────────────────────────────────────────────
    prompt: str = Field(
        min_length=1,
        max_length=2000,
        description="Prompt de texto para geração do vídeo",
    )
    model: str = Field(
        default="animatediff",
        description="Modelo de IA a usar (animatediff, wan2.1, cogvideox, hunyuan)",
    )

    # ── Parâmetros de geração ───────────────────────────────────────────────
    duration_seconds: int = Field(
        default=5,
        ge=1,
        le=60,
        description="Duração do vídeo em segundos (1-60)",
    )
    width: int = Field(
        default=848,
        ge=64,
        le=1920,
        description="Largura em pixels (múltiplo de 8, 64-1920)",
    )
    height: int = Field(
        default=480,
        ge=64,
        le=1080,
        description="Altura em pixels (múltiplo de 8, 64-1080)",
    )

    # ── Estado do job ──────────────────────────────────────────────────────
    status: JobStatus = Field(
        default=JobStatus.PENDING,
        description="Status atual do job",
    )
    output_path: str | None = Field(
        default=None,
        description="Caminho local do vídeo gerado (preenchido quando completed)",
    )
    error_message: str | None = Field(
        default=None,
        description="Mensagem de erro (preenchido quando failed)",
    )

    # ── Timestamps ─────────────────────────────────────────────────────────
    created_at: datetime = Field(
        default_factory=_utcnow,
        description="Timestamp de criação (UTC)",
    )
    updated_at: datetime = Field(
        default_factory=_utcnow,
        description="Timestamp da última atualização (UTC)",
    )
