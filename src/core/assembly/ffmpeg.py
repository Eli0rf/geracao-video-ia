"""
src/core/assembly/ffmpeg.py — Montagem do vídeo final via FFmpeg (subprocess).

Concatena os clipes das cenas (concat demuxer), normaliza resolução/fps e
faz o mux da trilha de áudio (narração do Piper) em um único MP4.

Decisões (ADR-007):
    - FFmpeg direto via `subprocess.run([...], shell=False)` — sem MoviePy.
    - Construção dos comandos em **funções puras** (testáveis sem o binário).
    - Dois passos: (1) concat + normalização, (2) mux de áudio.
"""

import shutil
import subprocess
import tempfile
from pathlib import Path

import structlog

from src.core.errors import AssemblyError, GenerationTimeoutError

logger = structlog.get_logger(__name__)

_DEFAULT_FPS = 24


def build_concat_list(clips: list[Path]) -> str:
    """
    Monta o conteúdo do arquivo de lista do concat demuxer do FFmpeg.

    Args:
        clips: Caminhos dos clipes, na ordem desejada.

    Returns:
        Texto com uma linha `file '<abs>'` por clipe.
    """
    lines = [f"file '{Path(c).resolve()}'" for c in clips]
    return "\n".join(lines) + "\n"


def build_concat_command(
    list_path: Path,
    out_path: Path,
    width: int,
    height: int,
    fps: int = _DEFAULT_FPS,
) -> list[str]:
    """
    Comando FFmpeg do passo 1: concatenar clipes e normalizar resolução/fps.

    Reencoda o vídeo (`libx264`, `yuv420p`) aplicando `scale` + `fps` e
    descarta qualquer áudio dos clipes (`-an`).
    """
    vf = f"scale={width}:{height},fps={fps}"
    return [
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(list_path),
        "-vf",
        vf,
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-an",
        str(out_path),
    ]


def build_mux_command(video_path: Path, audio_path: Path, out_path: Path) -> list[str]:
    """
    Comando FFmpeg do passo 2: mixar o áudio da narração com o vídeo.

    Copia o stream de vídeo (`-c:v copy`) e encoda o áudio em AAC; `-shortest`
    ajusta a saída à menor das durações.
    """
    return [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-i",
        str(audio_path),
        "-map",
        "0:v",
        "-map",
        "1:a",
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-shortest",
        str(out_path),
    ]


class VideoAssembler:
    """
    Monta o vídeo final concatenando clipes e mixando o áudio da narração.

    Args:
        binary: Nome/caminho do executável `ffmpeg` (default das settings).
        timeout: Timeout por comando FFmpeg, em segundos (default settings).
        fps: Framerate de normalização do vídeo concatenado.
    """

    def __init__(
        self,
        binary: str | None = None,
        timeout: float | None = None,
        fps: int = _DEFAULT_FPS,
    ) -> None:
        from src.config import get_settings

        settings = get_settings()
        self._binary = binary or settings.ffmpeg_binary
        self._timeout = timeout if timeout is not None else settings.ffmpeg_timeout_seconds
        self._fps = fps

    def is_available(self) -> bool:
        """True se o binário `ffmpeg` existe no PATH."""
        return shutil.which(self._binary) is not None

    def assemble(
        self,
        clips: list[Path],
        audio: Path,
        out_path: Path,
        width: int,
        height: int,
    ) -> Path:
        """
        Concatena `clips`, normaliza para `width`x`height` e mixa `audio`.

        Args:
            clips: Clipes de vídeo das cenas (ordem importa).
            audio: Arquivo de áudio da narração (WAV do Piper).
            out_path: Caminho do MP4 final de saída.
            width: Largura alvo em pixels.
            height: Altura alvo em pixels.

        Returns:
            O próprio `out_path` (MP4 final).

        Raises:
            AssemblyError: Clipes vazios, binário ausente ou FFmpeg falhou.
            GenerationTimeoutError: FFmpeg excedeu o tempo limite.
        """
        if not clips:
            raise AssemblyError("Nenhum clipe fornecido para montagem.")

        if shutil.which(self._binary) is None:
            raise AssemblyError(f"Binário FFmpeg '{self._binary}' não encontrado no PATH.")

        out_path.parent.mkdir(parents=True, exist_ok=True)

        with tempfile.TemporaryDirectory(prefix="gvassembly_") as tmp:
            tmp_dir = Path(tmp)
            list_path = tmp_dir / "concat.txt"
            list_path.write_text(build_concat_list(clips), encoding="utf-8")
            intermediate = tmp_dir / "concat.mp4"

            concat_cmd = self._resolve(
                build_concat_command(list_path, intermediate, width, height, self._fps)
            )
            self._run(concat_cmd)

            mux_cmd = self._resolve(build_mux_command(intermediate, audio, out_path))
            self._run(mux_cmd)

        logger.info(
            "video_assembled",
            clips=len(clips),
            width=width,
            height=height,
            out=str(out_path),
        )
        return out_path

    def _resolve(self, cmd: list[str]) -> list[str]:
        """Substitui o placeholder 'ffmpeg' pelo caminho absoluto do binário."""
        return [self._binary, *cmd[1:]]

    def _run(self, cmd: list[str]) -> None:
        """Executa um comando FFmpeg, convertendo falhas em erros de domínio."""
        try:
            result = subprocess.run(  # noqa: S603 — lista de args, sem shell
                cmd,
                capture_output=True,
                timeout=self._timeout,
                check=False,
                shell=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise GenerationTimeoutError(
                f"FFmpeg excedeu o tempo limite de {self._timeout}s."
            ) from exc

        if result.returncode != 0:
            stderr = result.stderr.decode("utf-8", "replace") if result.stderr else ""
            raise AssemblyError(f"FFmpeg falhou (code={result.returncode}): {stderr}")
