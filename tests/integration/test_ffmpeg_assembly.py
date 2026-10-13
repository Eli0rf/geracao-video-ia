"""
Testes de integração do VideoAssembler (src/core/assembly/ffmpeg.py).

Executam o FFmpeg REAL para validar a montagem de ponta a ponta. São
ignorados automaticamente quando o binário `ffmpeg` não está no PATH
(ambientes sem FFmpeg instalado), via pytest.mark.skipif.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

from src.core.assembly.ffmpeg import VideoAssembler

pytestmark = pytest.mark.skipif(
    shutil.which("ffmpeg") is None,
    reason="ffmpeg não instalado no ambiente",
)

# Binário resolvido para caminho absoluto (evita S607 e é mais robusto).
_FFMPEG = shutil.which("ffmpeg") or "ffmpeg"


def _make_clip(path: Path, color: str, seconds: int = 1) -> Path:
    """Gera um clipe MP4 mínimo e silencioso via fonte lavfi do FFmpeg."""
    cmd = [
        _FFMPEG,
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"color=c={color}:s=320x240:d={seconds}:r=24",
        "-pix_fmt",
        "yuv420p",
        str(path),
    ]
    result = subprocess.run(cmd, capture_output=True, check=False, shell=False)  # noqa: S603
    assert result.returncode == 0, result.stderr.decode("utf-8", "replace")
    return path


def _make_audio(path: Path, seconds: int = 2) -> Path:
    """Gera um áudio WAV mínimo (silêncio) via fonte lavfi do FFmpeg."""
    cmd = [
        _FFMPEG,
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"anullsrc=r=22050:cl=mono:d={seconds}",
        str(path),
    ]
    result = subprocess.run(cmd, capture_output=True, check=False, shell=False)  # noqa: S603
    assert result.returncode == 0, result.stderr.decode("utf-8", "replace")
    return path


class TestRealAssembly:
    def test_assembles_clips_with_audio(self, tmp_path: Path) -> None:
        clips = [
            _make_clip(tmp_path / "c0.mp4", "red"),
            _make_clip(tmp_path / "c1.mp4", "blue"),
        ]
        audio = _make_audio(tmp_path / "narracao.wav")
        out = tmp_path / "final.mp4"

        result = VideoAssembler().assemble(clips, audio, out, 320, 240)

        assert result == out
        assert out.exists()
        assert out.stat().st_size > 0

    def test_output_is_readable_mp4(self, tmp_path: Path) -> None:
        clip = _make_clip(tmp_path / "c0.mp4", "green")
        audio = _make_audio(tmp_path / "a.wav")
        out = tmp_path / "final.mp4"

        VideoAssembler().assemble([clip], audio, out, 320, 240)

        # Valida via ffprobe (se disponível) que há 1 stream de vídeo + 1 de áudio
        ffprobe = shutil.which("ffprobe")
        if ffprobe is None:
            pytest.skip("ffprobe não instalado")
        probe = subprocess.run(  # noqa: S603
            [
                ffprobe,
                "-v",
                "error",
                "-show_entries",
                "stream=codec_type",
                "-of",
                "csv=p=0",
                str(out),
            ],
            capture_output=True,
            check=False,
            shell=False,
        )
        streams = probe.stdout.decode().split()
        assert "video" in streams
        assert "audio" in streams
