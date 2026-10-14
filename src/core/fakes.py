"""
src/core/fakes.py — Implementações falsas determinísticas dos contratos.

Usadas em testes e como fallback quando o serviço real está indisponível
(ex.: CI sem Ollama/Piper). Não fazem I/O de rede nem dependem de modelos.

Geram arquivos mínimos válidos o suficiente para o pipeline prosseguir:
    - Script: cena única determinística derivada do prompt.
    - Áudio: WAV PCM de silêncio de 1s, gerado via ffmpeg lavfi
      (ou via biblioteca nativa `wave` se ffmpeg não estiver disponível).
    - Vídeo: MP4 real de tela preta, gerado via lavfi `color=black`
      (respeita width/height/duration do job; requer ffmpeg).
"""

import shutil
import subprocess
import wave
from pathlib import Path

from src.core.interfaces import Scene, Script


class FakeVideoGenerator:
    """
    `VideoGenerator` falso que gera um MP4 real via lavfi (tela preta).

    Usa o `ffmpeg` do contêiner (disponível na imagem `python:3.11-slim`).
    Nada de placeholder de 1 byte. O arquivo gerado é uma tela preta codificada
    com libx264 e yuv420p, compatível com o VideoAssembler.
    """

    def __init__(self, name: str = "fake", min_vram_gb: int = 0) -> None:
        self._name = name
        self._min_vram_gb = min_vram_gb

    @property
    def name(self) -> str:
        return self._name

    @property
    def min_vram_gb(self) -> int:
        return self._min_vram_gb

    def is_available(self) -> bool:
        # Fakes são "sempre disponíveis" como contrato; a geração real de
        # mídia só consolida (e gera MP4/WAV válidos) quando há ffmpeg no
        # contêiner que executa o pipeline.
        return True

    def generate(self, prompt: str, out_path: Path, **kwargs: object) -> Path:
        """Gera um MP4 real via lavfi (tela preta) em `out_path` e o retorna.

        Durante testes locais (sem ffmpeg), gera um placeholder seguro que
        mantém o pipeline acionável; em produção (contêiner) o `ffmpeg` do
        sistema gera o MV real via lavfi.
        """
        out_path.parent.mkdir(parents=True, exist_ok=True)
        width = int(kwargs.get("width", 848))  # type: ignore[call-overload]
        height = int(kwargs.get("height", 480))  # type: ignore[call-overload]
        duration = float(kwargs.get("duration_seconds", 5))  # type: ignore[arg-type]

        if shutil.which("ffmpeg") is not None:
            cmd = [
                "ffmpeg", "-y", "-loglevel", "error",
                "-f", "lavfi",
                "-i", f"color=c=black:s={width}x{height}:d={duration}",
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-an",
                str(out_path),
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise RuntimeError(
                    f"ffmpeg falhou ao gerar vídeo: {result.stderr}"
                )
            return out_path

        # Fallback local (sem ffmpeg): arquivo placeholder que não quebra o
        # pipeline, só não é reproduzível. A partir do contêiner, o ffmpeg
        # realiza a geração de verdade.
        out_path.write_bytes(b"FAKE-VIDEO-MP4")
        return out_path


class FakeScriptGenerator:
    """
    `ScriptGenerator` falso — produz uma cena única determinística.

    Útil para testar o pipeline sem Ollama instalado.
    """

    def is_available(self) -> bool:
        return True

    def generate_script(self, prompt: str) -> Script:
        """Retorna um roteiro com uma única cena derivada do prompt."""
        scene = Scene(narration=prompt, visual_prompt=prompt)
        return Script(scenes=(scene,), source_prompt=prompt)


class FakeAudioSynthesizer:
    """
    `AudioSynthesizer` falso — grava um WAV PCM de silêncio válido.

    Gera 1 segundo de silêncio via ffmpeg lavfi `anullsrc` (16-bit mono,
    22050 Hz). Se o ffmpeg não estiver disponível (não no contêiner), usa a
    biblioteca nativa `wave` como fallback.
    """

    _SAMPLE_RATE = 22050

    def is_available(self) -> bool:
        # Fakes são "sempre disponíveis" como contrato; a síntese real só
        # consolida (WAV válido) quando há ffmpeg no contêiner.
        return True

    def synthesize(self, text: str, out_path: Path) -> Path:
        """Grava 1s de silêncio em `out_path` (WAV) e o retorna."""
        out_path.parent.mkdir(parents=True, exist_ok=True)

        if shutil.which("ffmpeg") is None:
            # Fallback nativo: gerador de onda via `wave` (stdlib).
            n_samples = self._SAMPLE_RATE
            with wave.open(str(out_path), "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(self._SAMPLE_RATE)
                wav.writeframes(b"\x00\x00" * n_samples)
            return out_path

        cmd = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "lavfi",
            "-i", f"anullsrc=channel_layout=mono:sample_rate={self._SAMPLE_RATE}",
            "-t", "1",
            "-c:a", "pcm_s16le",
            str(out_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg falhou ao gerar áudio: {result.stderr}")
        return out_path
