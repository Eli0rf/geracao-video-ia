"""
src/core/generators/animatediff.py — Gerador de vídeo via AnimateDiff (diffusers).

Implementa `VideoGenerator` usando `AnimateDiffPipeline` da biblioteca
`diffusers` (extra `ai`). Pensado para Apple Silicon: usa o backend Metal
(`mps`) quando disponível, com fallback para `cpu` (vide ADR-003).

Imports de `torch`/`diffusers` são lazy (dentro dos métodos) para que o
módulo importe sem o extra `ai` instalado — `is_available()` retorna False
nesse caso e a factory cai para o fake.
"""

import sys
from pathlib import Path
from typing import Any

import structlog

from src.core.errors import GenerationError, GenerationTimeoutError

logger = structlog.get_logger(__name__)

_DEFAULT_MODEL_ID = "guoyww/animatediff-motion-adapter-v1-5-2"
_DEFAULT_FPS = 8
_MIN_VRAM_GB = 4


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


class AnimateDiffGenerator:
    """
    `VideoGenerator` real baseado no AnimateDiff (diffusers).

    Args:
        model_id: ID do modelo no HuggingFace Hub (default motion-adapter).
        device: `mps`/`cpu` explícito; None resolve automaticamente.
        force_cpu: Força CPU mesmo com MPS disponível.
        num_inference_steps: Passos de difusão por geração.
        timeout: Timeout da geração em segundos (default das settings).
    """

    def __init__(
        self,
        model_id: str | None = None,
        device: str | None = None,
        force_cpu: bool | None = None,
        num_inference_steps: int = 25,
        timeout: float | None = None,
    ) -> None:
        from src.config import get_settings

        settings = get_settings()
        self._model_id = model_id or _DEFAULT_MODEL_ID
        _force = force_cpu if force_cpu is not None else settings.force_cpu
        self._device = device or resolve_device(force_cpu=_force)
        self._num_inference_steps = num_inference_steps
        self._timeout = timeout if timeout is not None else settings.job_timeout_seconds
        self._pipe: Any = None

    @property
    def name(self) -> str:
        return "animatediff"

    @property
    def min_vram_gb(self) -> int:
        return _MIN_VRAM_GB

    @property
    def device(self) -> str:
        return self._device

    @staticmethod
    def is_available_static() -> bool:
        """True se torch + diffusers importáveis (sem carregar pesos)."""
        try:
            import diffusers  # noqa: F401
            import torch  # noqa: F401
        except ImportError:
            return False
        return True

    def is_available(self) -> bool:
        """True se as deps do extra `ai` estão instaladas."""
        return self.is_available_static()

    def _load_pipeline(self) -> Any:
        """Carrega (com cache) o AnimateDiffPipeline no device resolvido."""
        if self._pipe is not None:
            return self._pipe
        try:
            from diffusers import AnimateDiffPipeline
        except ImportError as exc:
            raise GenerationError(
                "diffusers/torch não instalados (extra `ai`). "
                "Instale com: pip install -e '.[ai]'."
            ) from exc
        try:
            pipe = AnimateDiffPipeline.from_pretrained(self._model_id)
            if hasattr(pipe, "to"):
                pipe = pipe.to(self._device)
            self._pipe = pipe
            return pipe
        except Exception as exc:
            raise GenerationError(
                f"AnimateDiff: falha ao carregar {self._model_id}: {exc}"
            ) from exc

    def generate(self, prompt: str, out_path: Path, **kwargs: object) -> Path:
        """
        Gera um clipe MP4 a partir do prompt via AnimateDiff.

        Raises:
            GenerationError: Falha no pipeline ou exportação.
            GenerationTimeoutError: Geração excedeu o timeout.
        """
        import concurrent.futures

        out_path.parent.mkdir(parents=True, exist_ok=True)
        duration = float(kwargs.get("duration_seconds", 2))  # type: ignore[arg-type]
        width = int(kwargs.get("width", 512))  # type: ignore[call-overload]
        height = int(kwargs.get("height", 512))  # type: ignore[call-overload]
        n_def = max(8, int(duration * _DEFAULT_FPS))
        num_frames = int(kwargs.get("num_frames", n_def))  # type: ignore[call-overload]
        fps = int(kwargs.get("fps", _DEFAULT_FPS))  # type: ignore[call-overload]

        def _run() -> Path:
            pipe = self._load_pipeline()
            try:
                output = pipe(
                    prompt,
                    num_frames=num_frames,
                    num_inference_steps=self._num_inference_steps,
                    height=height,
                    width=width,
                )
            except Exception as exc:
                raise GenerationError(f"AnimateDiff falhou na inferência: {exc}") from exc
            frames = getattr(output, "frames", None)
            if frames is None:
                frames = getattr(output, "images", None)
            if frames is None:
                raise GenerationError("AnimateDiff retornou saída sem frames.")
            if isinstance(frames, list) and frames and isinstance(frames[0], list):
                frames = frames[0]
            self._export_frames(frames, out_path, fps)
            return out_path

        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(_run)
                return future.result(timeout=self._timeout)
        except concurrent.futures.TimeoutError as exc:
            raise GenerationTimeoutError(
                f"AnimateDiff excedeu o tempo limite de {self._timeout}s."
            ) from exc
        except GenerationError:
            raise
        except Exception as exc:
            raise GenerationError(f"AnimateDiff falhou: {exc}") from exc

    def _export_frames(self, frames: Any, out_path: Path, fps: int) -> None:
        """Exporta frames para MP4 via diffusers ou imageio (fallback)."""
        try:
            from diffusers.utils import export_to_video

            export_to_video(frames, str(out_path), fps=fps)
            logger.info("animatediff_exported", out=str(out_path), fps=fps)
            return
        except ImportError:
            pass
        except Exception as exc:
            raise GenerationError(
                f"AnimateDiff falhou ao exportar vídeo: {exc}"
            ) from exc
        try:
            import imageio

            imageio.mimsave(str(out_path), frames, fps=fps)
            logger.info("animatediff_exported_imageio", out=str(out_path), fps=fps)
        except ImportError as exc:
            raise GenerationError(
                "Nenhum exportador de vídeo (diffusers/imageio) disponível."
            ) from exc
        except Exception as exc:
            raise GenerationError(
                f"AnimateDiff falhou ao exportar vídeo: {exc}"
            ) from exc
