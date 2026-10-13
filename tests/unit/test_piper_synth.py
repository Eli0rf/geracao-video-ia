"""
Testes para PiperAudioSynthesizer (src/core/generators/piper.py).

Mocka subprocess.run e shutil.which — sem binário Piper real.
"""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.core.errors import GenerationError, GenerationTimeoutError
from src.core.generators.piper import PiperAudioSynthesizer


class TestIsAvailable:
    def test_available_when_binary_and_voice_present(self, tmp_path: Path) -> None:
        voice = tmp_path / "voice.onnx"
        voice.write_text("fake")
        synth = PiperAudioSynthesizer(binary="piper", voice_path=voice)
        with patch("shutil.which", return_value="/usr/bin/piper"):
            assert synth.is_available() is True

    def test_unavailable_when_binary_missing(self, tmp_path: Path) -> None:
        voice = tmp_path / "voice.onnx"
        voice.write_text("fake")
        synth = PiperAudioSynthesizer(binary="piper", voice_path=voice)
        with patch("shutil.which", return_value=None):
            assert synth.is_available() is False

    def test_unavailable_when_voice_missing(self, tmp_path: Path) -> None:
        synth = PiperAudioSynthesizer(
            binary="piper", voice_path=tmp_path / "nao_existe.onnx"
        )
        with patch("shutil.which", return_value="/usr/bin/piper"):
            assert synth.is_available() is False


class TestSynthesize:
    def _synth(self, tmp_path: Path, **kw: object) -> PiperAudioSynthesizer:
        voice = tmp_path / "voice.onnx"
        voice.write_text("fake")
        return PiperAudioSynthesizer(binary="piper", voice_path=voice, **kw)  # type: ignore[arg-type]

    def test_success_creates_file_and_correct_args(self, tmp_path: Path) -> None:
        synth = self._synth(tmp_path)
        out = tmp_path / "sub" / "audio.wav"
        fake_run = MagicMock(return_value=subprocess.CompletedProcess([], 0))
        with (
            patch("shutil.which", return_value="/usr/bin/piper"),
            patch("subprocess.run", fake_run),
        ):
            result = synth.synthesize("olá mundo", out)

        assert result == out
        assert out.parent.exists()
        cmd = fake_run.call_args.args[0]
        assert cmd[0] == "/usr/bin/piper"
        assert str(out) in cmd
        assert str(synth._voice_path) in cmd
        # texto vai via stdin, não como argumento de comando
        assert "olá mundo" not in cmd
        assert fake_run.call_args.kwargs["input"] == "olá mundo".encode()
        assert fake_run.call_args.kwargs["shell"] is False

    def test_nonzero_return_raises(self, tmp_path: Path) -> None:
        synth = self._synth(tmp_path)
        out = tmp_path / "audio.wav"
        fake_run = MagicMock(
            return_value=subprocess.CompletedProcess([], 1, b"", b"erro piper")
        )
        with (
            patch("shutil.which", return_value="/usr/bin/piper"),
            patch("subprocess.run", fake_run),
        ):
            with pytest.raises(GenerationError, match="Piper falhou"):
                synth.synthesize("x", out)

    def test_timeout_raises_timeout_error(self, tmp_path: Path) -> None:
        synth = self._synth(tmp_path, timeout=5)
        out = tmp_path / "audio.wav"
        fake_run = MagicMock(side_effect=subprocess.TimeoutExpired("piper", 5))
        with (
            patch("shutil.which", return_value="/usr/bin/piper"),
            patch("subprocess.run", fake_run),
        ):
            with pytest.raises(GenerationTimeoutError):
                synth.synthesize("x", out)

    def test_binary_missing_raises(self, tmp_path: Path) -> None:
        synth = self._synth(tmp_path)
        out = tmp_path / "audio.wav"
        with patch("shutil.which", return_value=None):
            with pytest.raises(GenerationError, match="não encontrado"):
                synth.synthesize("x", out)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

