"""
src/models/video_job_crud.py — Operações CRUD para VideoJob.

Funções puras que recebem uma Session e operam sobre VideoJob.
Sem lógica de negócio — apenas persistência.
"""

from datetime import UTC, datetime

from sqlmodel import Session, func, select

from src.models.video_job import JobStatus, VideoJob


def create_video_job(
    session: Session,
    prompt: str,
    model: str = "animatediff",
    duration_seconds: int = 5,
    width: int = 848,
    height: int = 480,
) -> VideoJob:
    """
    Persiste um novo VideoJob com status PENDING.

    Args:
        session: Sessão SQLModel ativa.
        prompt: Texto descritivo para geração do vídeo.
        model: Modelo de IA a usar.
        duration_seconds: Duração do vídeo em segundos.
        width: Largura em pixels.
        height: Altura em pixels.

    Returns:
        VideoJob recém-criado e persistido.
    """
    job = VideoJob(
        prompt=prompt,
        model=model,
        duration_seconds=duration_seconds,
        width=width,
        height=height,
    )
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


def get_video_job(session: Session, job_id: str) -> VideoJob | None:
    """
    Busca um VideoJob pelo ID.

    Args:
        session: Sessão SQLModel ativa.
        job_id: UUID do job.

    Returns:
        VideoJob encontrado ou None se não existir.
    """
    return session.get(VideoJob, job_id)


def list_video_jobs(
    session: Session,
    page: int = 1,
    page_size: int = 20,
    status: JobStatus | None = None,
) -> tuple[list[VideoJob], int]:
    """
    Lista VideoJobs com paginação e filtro opcional por status.

    Ordenação: mais recente primeiro (created_at DESC).

    Args:
        session: Sessão SQLModel ativa.
        page: Página atual (1-indexed).
        page_size: Número de itens por página (máx. 100).
        status: Filtro por status (opcional).

    Returns:
        Tupla (lista de jobs, total de registros).
    """
    # Sanitização: garante valores mínimos válidos
    page = max(1, page)
    page_size = max(1, min(page_size, 100))
    offset = (page - 1) * page_size

    # Contagem eficiente via SQL (sem carregar objetos em memória)
    count_stmt = select(func.count()).select_from(VideoJob)
    items_stmt = select(VideoJob)

    if status is not None:
        count_stmt = count_stmt.where(VideoJob.status == status)
        items_stmt = items_stmt.where(VideoJob.status == status)

    # Total via COUNT no banco
    total = session.exec(count_stmt).one()

    # Items paginados, mais recente primeiro
    items_stmt = items_stmt.order_by(VideoJob.created_at.desc()).offset(offset).limit(page_size)  # type: ignore[attr-defined]
    jobs = list(session.exec(items_stmt).all())

    return jobs, total


def update_job_status(
    session: Session,
    job_id: str,
    status: JobStatus,
    output_path: str | None = None,
    error_message: str | None = None,
) -> VideoJob | None:
    """
    Atualiza o status de um VideoJob.

    Args:
        session: Sessão SQLModel ativa.
        job_id: UUID do job a atualizar.
        status: Novo status.
        output_path: Caminho do arquivo gerado (apenas para COMPLETED).
        error_message: Mensagem de erro (apenas para FAILED).

    Returns:
        VideoJob atualizado ou None se não encontrado.
    """
    job = session.get(VideoJob, job_id)
    if job is None:
        return None

    job.status = status
    job.updated_at = datetime.now(UTC)

    if output_path is not None:
        job.output_path = output_path
    if error_message is not None:
        job.error_message = error_message

    session.add(job)
    session.commit()
    session.refresh(job)
    return job
