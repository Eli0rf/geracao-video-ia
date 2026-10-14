"""
src/core/generators/wan.py — Gerador de vídeo via Wan2.1 (diffusers).

Implementa `VideoGenerator` usando `WanPipeline` (text-to-video) da
biblioteca `diffusers>=0.33` (extra `ai`). Segue o mesmo padrão do
AnimateDiff: device MPS (Apple Silicon) com fallback CPU, imports lazy,
timeout via ThreadPoolExecutor e exportação via diffusers/imageio.

Otimização de VRAM: após `.to(device)`, aplica `enable_attention_slicing()`
quando disponível (crucial em Macs 8-16GB de memória unificada).
"""

from pathlib import Path
from typing import Any

import structlog

from src.core.devices import resolve_device
from src.core.errors import GenerationError, GenerationTimeoutError

logger = structlog.get_logger(__name__)

_DEFAULT_MODEL_ID = "Wan-AI/Wan2.1-T2V-1.3B-Diffusers"
_DEFAULT_FPS = 16
_DEFAULT_GUIDANCE_SCALE = 5.0
_DEFAULT_NEGATIVE_PROMPT = (
    "Bright tones, overexposed, static, blurred details, subtitles, "
    "style, works, paintings, images, static, overall gray, worst quality, "
    "low quality, JPEG compression residue, ugly, incomplete, extra fingers, "
    "poorly drawn hands, poorly drawn faces, deformed, disfigured"
)
_MIN_VRAM_GB = 8


class WanVideoGenerator:
    """
    `VideoGenerator` real baseado no Wan2.1 T2V (diffusers>=0.33).

    Args:
        model_id: ID no HuggingFace Hub (default 1.3B, ~8GB VRAM).
        device: `mps`/`cpu` explícito; None resolve automaticamente.
        force_cpu: Força CPU mesmo com MPS disponível.
        num_inference_steps: Passos de difusão por geração.
        guidance_scale: Escala de guidance (CFG).
        timeout: Timeout da geração em segundos (default das settings).
    """

    def __init__(
        self,
        model_id: str | None = None,
        device: str | None = None,
        force_cpu: bool | None = None,
        num_inference_steps: int = 50,
        guidance_scale: float = _DEFAULT_GUIDANCE_SCALE,
        timeout: float | None = None,
    ) -> None:
        from src.config import get_settings

        settings = get_settings()
        self._model_id = model_id or _DEFAULT_MODEL_ID
        _force = force_cpu if force_cpu is not None else settings.force_cpu
        self._device = device or resolve_device(force_cpu=_force)
        self._num_inference_steps = num_inference_steps
        self._guidance_scale = guidance_scale
        self._timeout = timeout if timeout is not None else settings.job_timeout_seconds
        self._pipe: Any = None

    @property
    def name(self) -> str:
        return "wan2.1"

    @property
    def min_vram_gb(self) -> int:
        return _MIN_VRAM_GB

    @property
    def device(self) -> str:
        return self._device

    @staticmethod
    def is_available_static() -> bool:
        """True se torch + WanPipeline importáveis (sem carregar pesos)."""
        try:
            import torch  # noqa: F401
            from diffusers import WanPipeline  # noqa: F401
        except ImportError:
            return False
        return True

    def is_available(self) -> bool:
        """True se as deps do extra `ai` (diffusers>=0.33) estão instaladas."""
        return self.is_available_static()

    def _load_pipeline(self) -> Any:
        """Carrega (com cache) o WanPipeline T2V com otimização de VRAM."""
        if self._pipe is not None:
            return self._pipe
        try:
            from diffusers import WanPipeline
        except ImportError as exc:
            raise GenerationError(
                "diffusers/torch não instalados ou sem WanPipeline "
                "(extra `ai` com diffusers>=0.33). "
                "Instale com: pip install -e '.[ai]'."
            ) from exc
        except AttributeError as exc:
            raise GenerationError(
                "WanPipeline ausente: atualize diffusers para >=0.33."
            ) from exc
        try:
            pipe = WanPipeline.from_pretrained(self._model_id)
            if hasattr(pipe, "to"):
                pipe = pipe.to(self._device)
            # Otimização de VRAM: essencial em Macs 8-16GB unificados.
            if hasattr(pipe, "enable_attention_slicing"):
                pipe.enable_attention_slicing()
            self._pipe = pipe
            return pipe
        except GenerationError:
            raise
        except Exception as exc:
            raise GenerationError(
                f"Wan2.1: falha ao carregar {self._model_id}: {exc}"
            ) from exc

    def generate(self, prompt: str, out_path: Path, **kwargs: object) -> Path:
        """
        Gera um clipe MP4 a partir do prompt via Wan2.1 T2V.

        Raises:
            GenerationError: Falha no pipeline ou exportação.
            GenerationTimeoutError: Geração excedeu o timeout.
        """
        import concurrent.futures

        out_path.parent.mkdir(parents=True, exist_ok=True)
        duration = float(kwargs.get("duration_seconds", 2))  # type: ignore[arg-type]
        width = int(kwargs.get("width", 832))  # type: ignore[call-overload]
        height = int(kwargs.get("height", 480))  # type: ignore[call-overload]
        n_def = max(16, int(duration * _DEFAULT_FPS))
        num_frames = int(kwargs.get("num_frames", n_def))  # type: ignore[call-overload]
        fps = int(kwargs.get("fps", _DEFAULT_FPS))  # type: ignore[call-overload]
        guidance = float(kwargs.get("guidance_scale", self._guidance_scale))  # type: ignore[arg-type]
        negative = str(kwargs.get("negative_prompt", _DEFAULT_NEGATIVE_PROMPT))

        def _run() -> Path:
            pipe = self._load_pipeline()
            try:
                output = pipe(
                    prompt=prompt,
                    negative_prompt=negative,
                    height=height,
                    width=width,
                    num_frames=num_frames,
                    guidance_scale=guidance,
                    num_inference_steps=self._num_inference_steps,
                )
            except Exception as exc:
                raise GenerationError(f"Wan2.1 falhou na inferência: {exc}") from exc
            frames = getattr(output, "frames", None)
            if frames is None:
                raise GenerationError("Wan2.1 retornou saída sem frames.")
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
                f"Wan2.1 excedeu o tempo limite de {self._timeout}s."
            ) from exc
        except GenerationError:
            raise
        except Exception as exc:
            raise GenerationError(f"Wan2.1 falhou: {exc}") from exc

    def _export_frames(self, frames: Any, out_path: Path, fps: int) -> None:
        """Exporta frames para MP4 via diffusers ou imageio (fallback)."""
        try:
            from diffusers.utils import export_to_video

            export_to_video(frames, str(out_path), fps=fps)
            logger.info("wan_exported", out=str(out_path), fps=fps)
            return
        except ImportError:
            pass
        except Exception as exc:
            raise GenerationError(
                f"Wan2.1 falhou ao exportar vídeo: {exc}"
            ) from exc
        try:
            import imageio

            imageio.mimsave(str(out_path), frames, fps=fps)
            logger.info("wan_exported_imageio", out=str(out_path), fps=fps)
        except ImportError as exc:
            raise GenerationError(
                "Nenhum exportador de vídeo (diffusers/imageio) disponível."
            ) from exc
        except Exception as exc:
            raise GenerationError(
                f"Wan2.1 falhou ao exportar vídeo: {exc}"
            ) from exc


# Alias de compatibilidade com o nome citado em interfaces.py (ADR-003).
Wan21Generator = WanVideoGenerator
