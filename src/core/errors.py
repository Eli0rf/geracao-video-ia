"""
src/core/errors.py — Exceções de domínio do motor de geração.

Hierarquia única (`GenerationError`) para que o worker/pipeline capture
falhas de qualquer estágio (roteiro, áudio, vídeo, montagem) e converta em
`job.failed` com mensagem, sem vazar stack traces para a API (CONSTRAINTS).
"""


class GenerationError(Exception):
    """
    Erro base de qualquer estágio da geração de vídeo.

    Todas as falhas previstas do motor herdam desta classe, permitindo
    tratamento uniforme no worker.
    """


class ModelUnavailableError(GenerationError):
    """Modelo/serviço de IA indisponível (deps, VRAM ou binário ausente)."""


class GenerationTimeoutError(GenerationError):
    """Etapa excedeu o tempo limite configurado."""


class AssemblyError(GenerationError):
    """Falha na montagem do vídeo final (FFmpeg)."""
