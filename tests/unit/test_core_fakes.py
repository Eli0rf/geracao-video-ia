"""
Testes para as implementações falsas (src/core/fakes.py).

Verificam que as fakes produzem saídas determinísticas e arquivos válidos
(WAV real) para que o pipeline possa ser exercitado sem I/O de rede/modelo.
"""

import wave
from pathlib import Path

from src.core.fakes import (
    FakeAudioSynthesizer,
    FakeScriptGenerator,
    FakeVideoGenerator,
)


class TestFakeVideoGenerator:
    def test_always_available(self) -> None:
        assert FakeVideoGenerator().is_available() is True

    def test_default_name_and_vram(self) -> None:
        gen = FakeVideoGenerator()
        assert gen.name == "fake"
        assert gen.min_vram_gb == 0

    def test_custom_name(self) -> None:
        gen = FakeVideoGenerator(name="wan2.1", min_vram_gb=8)
        assert gen.name == "wan2.1"
        assert gen.min_vram_gb == 8

    def test_generate_creates_file(self, tmp_path: Path) -> None:
        gen = FakeVideoGenerator()
        out = tmp_path / "clip.mp4"
        returned = gen.generate("a cat", out)
        assert returned == out
        assert out.exists()

    def test_generate_creates_parent_dirs(self, tmp_path: Path) -> None:
        gen = FakeVideoGenerator()
        out = tmp_path / "nested" / "dir" / "clip.mp4"
        gen.generate("a cat", out)
        assert out.exists()


class TestFakeScriptGenerator:
    def test_always_available(self) -> None:
        assert FakeScriptGenerator().is_available() is True

    def test_single_scene_from_prompt(self) -> None:
        gen = FakeScriptGenerator()
        script = gen.generate_script("um gato na lua")
        assert len(script.scenes) == 1
        assert script.source_prompt == "um gato na lua"
        assert script.scenes[0].narration == "um gato na lua"

    def test_deterministic(self) -> None:
        gen = FakeScriptGenerator()
        a = gen.generate_script("mesmo prompt")
        b = gen.generate_script("mesmo prompt")
        assert a == b


class TestFakeAudioSynthesizer:
    def test_always_available(self) -> None:
        assert FakeAudioSynthesizer().is_available() is True

    def test_synthesize_creates_valid_wav(self, tmp_path: Path) -> None:
        synth = FakeAudioSynthesizer()
        out = tmp_path / "audio.wav"
        returned = synth.synthesize("olá mundo", out)
        assert returned == out
        assert out.exists()

        # O arquivo deve ser um WAV legível (formato, canais, framerate)
        with wave.open(str(out), "rb") as wav:
            assert wav.getnchannels() == 1
            assert wav.getframerate() == 22050
            assert wav.getnframes() > 0

    def test_synthesize_creates_parent_dirs(self, tmp_path: Path) -> None:
        synth = FakeAudioSynthesizer()
        out = tmp_path / "nested" / "audio.wav"
        synth.synthesize("texto", out)
        assert out.exists()
