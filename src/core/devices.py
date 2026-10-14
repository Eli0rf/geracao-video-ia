"""
src/core/devices.py — Resolução de dispositivo de computação (CPU/MPS).

Centraliza a detecção do backend Metal (Apple Silicon) para que todos os
geradores de vídeo (AnimateDiff, Wan2.1, futuros) compartilhem a mesma
lógica, sem dependências cruzadas entre módulos de geradores.

O import de `torch` é lazy (dentro da função) para que o módulo importe
sem o extra `ai` instalado.
"""

import sys


def _torch_has_mps() -> bool:
    """True se torch instalado e backend MPS (Apple Silicon) disponível."""
    torch_mod = sys.modules.get("torch")
    if torch_mod is None:
        try:
            import torch as torch_mod  # type: ignore[no-redef]
        except ImportError:
            return False
    try:
        return bool(torch_mod.backends.mps.is_available())  # type: ignore[union-attr]
    except Exception:
        return False


def resolve_device(force_cpu: bool = False) -> str:
    """
    Resolve o device do pipeline: `mps` se Metal disponível, senão `cpu`.

    Args:
        force_cpu: Quando True, força `cpu` mesmo com MPS (settings/debug).
    """
    if force_cpu:
        return "cpu"
    return "mps" if _torch_has_mps() else "cpu"
