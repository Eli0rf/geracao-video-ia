"""
src/core/fakes.py — Implementações falsas determinísticas dos contratos.

Usadas em testes e como fallback quando o serviço real está indisponível
(ex.: CI sem Ollama/Piper). Não fazem I/O de rede nem dependem de modelos.

Geram arquivos mínimos válidos o suficiente para o pipeline prosseguir:
    - Script: cena única determinística derivada do prompt.
    - Áudio: WAV PCM de silêncio (lido por FFmpeg).
    - Vídeo: arquivo placeholder de 1 byte (testes não executam FFmpeg real).
"""

import wave
from pathlib import Path

from src.core.interfaces import Scene, Script


class FakeVideoGenerator:
    """
    `VideoGenerator` falso que cria um arquivo placeholder.

    Nunca falha e está sempre disponível — usado como último fallback na
    factory quando nenhum modelo real pode ser carregado.
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
        return True

    def generate(self, prompt: str, out_path: Path, **kwargs: object) -> Path:
        """Cria um arquivo placeholder em `out_path` e o retorna."""
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(b"FAKE-VIDEO")
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

    O arquivo resultante é um WAV real (16-bit mono, 22050 Hz) para que o
    FFmpeg consiga lê-lo nas etapas de montagem.
    """

    _SAMPLE_RATE = 22050

    def is_available(self) -> bool:
        return True

    def synthesize(self, text: str, out_path: Path) -> Path:
        """Grava 1 segundo de silêncio em `out_path` como WAV e o retorna."""
        out_path.parent.mkdir(parents=True, exist_ok=True)
        n_samples = self._SAMPLE_RATE
        with wave.open(str(out_path), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(self._SAMPLE_RATE)
            wav.writeframes(b"\x00\x00" * n_samples)
        return out_path
