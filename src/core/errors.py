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


class ScriptValidationError(GenerationError):
    """
    Roteiro reprovado pelo auditor LLM após esgotar as tentativas (E11).

    Falha no estágio de roteiro — o job termina como `failed` antes de
    desperdiçar processamento na renderização de vídeo.
    """


def is_out_of_memory_error(exc: BaseException) -> bool:
    """
    Detecta erros de memória insuficiente (CUDA/MPS/CPU) para log dedicado.

    Args:
        exc: Exceção capturada (inferência, carga ou exportação).

    Returns:
        True se o nome da classe é `*OutOfMemoryError` ou a mensagem
        contém "out of memory" / "not enough memory".
    """
    if "OutOfMemoryError" in type(exc).__name__:
        return True
    message = str(exc).lower()
    return "out of memory" in message or "not enough memory" in message
