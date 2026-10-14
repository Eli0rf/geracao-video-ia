#!/usr/bin/env python3
"""
scripts/prefetch_models.py — Pré-aquecimento: baixa os pesos dos modelos (E07).

Executa apenas `from_pretrained()` com `torch_dtype` apropriado para forçar o
download dos tensores para o cache do HuggingFace — nenhum vídeo é gerado.

O cache respeita `HF_HOME` (no Docker: /app/models → ./models na máquina host).

Uso:
    python scripts/prefetch_models.py                 # todos os modelos
    python scripts/prefetch_models.py --model wan     # só o Wan2.1
    make prefetch                                     # via Makefile
"""

from __future__ import annotations

import argparse
import os
import sys

WAN_MODEL_ID = "Wan-AI/Wan2.1-T2V-1.3B-Diffusers"
ANIMATEDIFF_ADAPTER_ID = "guoyww/animatediff-motion-adapter-v1-5-2"
ANIMATEDIFF_BASE_ID = "runwayml/stable-diffusion-v1-5"


def _cache_hint() -> str:
    """Caminho do cache HF (HF_HOME ou default do huggingface_hub)."""
    return os.environ.get("HF_HOME") or os.path.expanduser("~/.cache/huggingface")


def prefetch_wan() -> None:
    """Baixa os pesos do Wan2.1 T2V (1.3B) para o cache."""
    import torch
    from diffusers import WanPipeline

    print(f"⬇️  Wan2.1: baixando pesos de {WAN_MODEL_ID} ...")
    WanPipeline.from_pretrained(WAN_MODEL_ID, torch_dtype=torch.float16)
    print(f"✅ Wan2.1 em cache ({WAN_MODEL_ID}).")


def prefetch_animatediff() -> None:
    """Baixa o MotionAdapter + base Stable Diffusion para o cache."""
    import torch
    from diffusers import AnimateDiffPipeline, MotionAdapter

    print(f"⬇️  AnimateDiff: baixando adapter {ANIMATEDIFF_ADAPTER_ID} ...")
    adapter = MotionAdapter.from_pretrained(
        ANIMATEDIFF_ADAPTER_ID, torch_dtype=torch.float16
    )
    print(f"⬇️  AnimateDiff: baixando base {ANIMATEDIFF_BASE_ID} ...")
    AnimateDiffPipeline.from_pretrained(
        ANIMATEDIFF_BASE_ID, motion_adapter=adapter, torch_dtype=torch.float16
    )
    print(f"✅ AnimateDiff em cache ({ANIMATEDIFF_BASE_ID}).")


def main(argv: list[str] | None = None) -> int:
    """Pré-baixa os modelos selecionados. Retorna 0 em sucesso, 1 em falha."""
    parser = argparse.ArgumentParser(
        description="Pré-baixa os pesos dos modelos de IA (sem gerar vídeo)."
    )
    parser.add_argument(
        "--model",
        choices=("wan", "animatediff", "all"),
        default="all",
        help="Qual modelo pré-baixar (default: all).",
    )
    args = parser.parse_args(argv)

    print(f"💾 Cache HuggingFace: {_cache_hint()}")
    targets = []
    if args.model in ("wan", "all"):
        targets.append(prefetch_wan)
    if args.model in ("animatediff", "all"):
        targets.append(prefetch_animatediff)

    try:
        for target in targets:
            target()
    except ImportError as exc:
        print(
            f"❌ Extra [ai] não instalado ({exc}). Instale com: pip install -e '.[ai]'",
            file=sys.stderr,
        )
        return 1
    except Exception as exc:
        print(f"❌ Pré-fetch falhou: {exc}", file=sys.stderr)
        return 1

    print("🎉 Pré-fetch concluído.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
