"""
src/core/generators/piper.py — Sintetizador de áudio (TTS) via binário Piper.

Implementa `AudioSynthesizer` invocando o binário `piper` local via
`subprocess` (lista de argumentos, sem shell) para sintetizar narração em
WAV. Vide ADR-006.

CPU-only, sem GPU/torch. `is_available()` verifica binário + arquivo de voz
sem executar subprocess.
"""

import shutil
import subprocess
from pathlib import Path

import structlog

from src.core.errors import GenerationError, GenerationTimeoutError

logger = structlog.get_logger(__name__)


class PiperAudioSynthesizer:
    """
    `AudioSynthesizer` real baseado no binário Piper TTS.

    Args:
        binary: Nome/caminho do executável `piper` (default das settings).
        voice_path: Caminho do modelo de voz `.onnx` (default das settings).
        timeout: Timeout do subprocesso em segundos (default das settings).
    """

    def __init__(
        self,
        binary: str | None = None,
        voice_path: str | Path | None = None,
        timeout: float | None = None,
    ) -> None:
        from src.config import get_settings

        settings = get_settings()
        self._binary = binary or settings.piper_binary
        self._voice_path = Path(voice_path or settings.piper_voice_path).expanduser()
        self._timeout = timeout if timeout is not None else settings.piper_timeout_seconds

    def is_available(self) -> bool:
        """True se o binário `piper` existe no PATH e o arquivo de voz existe."""
        if shutil.which(self._binary) is None:
            return False
        return self._voice_path.is_file()

    def synthesize(self, text: str, out_path: Path) -> Path:
        """
        Sintetiza `text` em `out_path` (WAV) invocando o binário Piper.

        Raises:
            GenerationTimeoutError: Subprocesso excedeu o tempo limite.
            GenerationError: Binário ausente ou Piper retornou código != 0.
        """
        out_path.parent.mkdir(parents=True, exist_ok=True)

        resolved = shutil.which(self._binary)
        if resolved is None:
            raise GenerationError(f"Binário Piper '{self._binary}' não encontrado no PATH.")

        cmd = [
            resolved,
            "--model",
            str(self._voice_path),
            "--output_file",
            str(out_path),
        ]
        try:
            result = subprocess.run(  # noqa: S603 — lista de args, sem shell, texto via stdin
                cmd,
                input=text.encode("utf-8"),
                capture_output=True,
                timeout=self._timeout,
                check=False,
                shell=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise GenerationTimeoutError(
                f"Piper excedeu o tempo limite de {self._timeout}s."
            ) from exc

        if result.returncode != 0:
            stderr = result.stderr.decode("utf-8", "replace") if result.stderr else ""
            raise GenerationError(f"Piper falhou (code={result.returncode}): {stderr}")

        logger.info("audio_synthesized", chars=len(text), out=str(out_path))
        return out_path
